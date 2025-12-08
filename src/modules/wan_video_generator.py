"""Text-to-video generator using Alibaba Wan T2V models"""
import subprocess
from pathlib import Path
from typing import Optional
import sys
import logging
import re

logger = logging.getLogger(__name__)


class WanVideoGenerator:
    """
    Integration for Alibaba Wan text-to-video generation models.
    Supports Wan2.1-T2V-1.3B (consumer GPUs) and Wan2.1-T2V-14B (high-end GPUs).
    """

    def __init__(self, config):
        self.config = config
        # Use absolute paths so subprocess calls resolve weights correctly
        self.repo_dir = Path(config.models.get('wan', {}).get('repo_dir', 'models/wan2.1')).resolve()
        self.model_dir = Path(config.models.get('wan', {}).get('model_dir', 'models/wan2.1-weights')).resolve()
        self.model_size = config.models.get('wan', {}).get('size', '1.3B')  # '1.3B' or '14B'
        self.max_duration = config.models.get('wan', {}).get('max_duration', 5)
        self.resolution = config.models.get('wan', {}).get('resolution', '832*480')  # or '1280*720'
        self.offload_model = config.models.get('wan', {}).get('offload_model', True)
        self.sample_shift = config.models.get('wan', {}).get('sample_shift', 8)
        self.sample_guide_scale = config.models.get('wan', {}).get('sample_guide_scale', 6)
        self.min_free_ram_gb = 6  # fail fast if system RAM is critically low

    def is_available(self) -> bool:
        """
        Return True if Wan repository and model weights exist.
        """
        repo_exists = (self.repo_dir.exists() and
                      (self.repo_dir / "generate.py").exists())
        model_exists = self.model_dir.exists() and any(self.model_dir.glob("*"))

        if not repo_exists:
            logger.warning(f"Wan repository not found at {self.repo_dir}")
        if not model_exists:
            logger.warning(f"Wan model weights not found at {self.model_dir}")

        return repo_exists and model_exists

    def generate(self, prompt: str, duration: float, output_path: str) -> str:
        """
        Generate a video from text using Wan T2V.

        Args:
            prompt: Text description of the video to generate
            duration: Desired video duration (limited by model, typically 5s)
            output_path: Where to save the generated video

        Returns:
            Path to generated video

        Raises:
            RuntimeError: If generation fails or prerequisites missing
        """
        if not self.is_available():
            raise RuntimeError(
                f"Wan T2V not available. Ensure:\n"
                f"1. Repository cloned at {self.repo_dir}\n"
                f"2. Model weights downloaded to {self.model_dir}\n"
                f"Run: python3 download_wan_weights.py"
            )

        self._ensure_ram_available()

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Determine task name
        task = f"t2v-{self.model_size}"

        # Build command
        script = "generate.py"  # run from repo_dir, avoid duplicated path
        cmd = [
            sys.executable,  # Use same Python as current environment
            script,
            "--task", task,
            "--size", self.resolution,
            "--ckpt_dir", str(self.model_dir),
            "--prompt", prompt,
            "--sample_shift", str(self.sample_shift),
            "--sample_guide_scale", str(self.sample_guide_scale),
        ]

        # Add memory optimization flags if enabled
        if self.offload_model:
            cmd.extend(["--offload_model", "True", "--t5_cpu"])

        logger.info(f"Generating video with Wan T2V ({self.model_size})")
        logger.info(f"Prompt: {prompt}")
        logger.info(f"Resolution: {self.resolution}")

        try:
            # Run generation
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                logger.error(f"Wan generation failed: {result.stderr}")
                if "size mismatch" in result.stderr.lower() and self.model_size == "1.3B":
                    raise RuntimeError(
                        "Wan reported size mismatches. The weights in "
                        f"{self.model_dir} look like a different model size than "
                        "requested (1.3B). Please remove the weights folder and "
                        "re-download the 1.3B checkpoint:\n"
                        "  rm -rf models/wan2.1-weights\n"
                        "  python3 download_wan_weights.py  # choose 1.3B\n"
                        "Then rerun with resolution 832*480."
                    )
                raise RuntimeError(
                    f"Wan T2V generation failed:\n{result.stderr}\n\n"
                    f"Command: {' '.join(cmd)}"
                )

            # Wan typically outputs to ./outputs/ directory
            # Find the most recent video file (prefer outputs/, fall back to repo root)
            output_dir = self.repo_dir / "outputs"
            search_dirs = [output_dir] if output_dir.exists() else []
            if not output_dir.exists():
                logger.warning(f"Wan outputs/ directory not found; searching repo root instead.")
                search_dirs.append(self.repo_dir)

            video_files = []
            for d in search_dirs:
                video_files.extend(list(d.glob("*.mp4")))
            video_files = sorted(video_files, key=lambda p: p.stat().st_mtime, reverse=True)

            if not video_files:
                raise RuntimeError(f"No video files found in {', '.join(str(d) for d in search_dirs)}")

            generated_video = video_files[0]

            # Move to desired output path
            import shutil
            shutil.move(str(generated_video), output_path)

            logger.info(f"Video generated successfully: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            raise RuntimeError("Wan T2V generation timed out (>10 minutes)")
        except Exception as e:
            logger.exception("Unexpected error during Wan generation")
            raise RuntimeError(f"Wan T2V generation error: {e}")

    def _ensure_repo_on_path(self):
        """Add Wan repository to sys.path for module discovery."""
        repo_str = str(self.repo_dir.resolve())
        if repo_str not in sys.path:
            sys.path.insert(0, repo_str)

    def _ensure_ram_available(self):
        """
        Fail early if available system RAM is too low. Uses /proc/meminfo to
        avoid extra dependencies. Best-effort: skips on non-Linux or parsing
        errors.
        """
        try:
            meminfo = Path("/proc/meminfo").read_text()
            match = re.search(r"MemAvailable:\s+(\d+)\s+kB", meminfo)
            if match:
                available_gb = int(match.group(1)) / (1024 ** 2)
                if available_gb < self.min_free_ram_gb:
                    raise RuntimeError(
                        f"Only {available_gb:.1f} GB RAM free. "
                        f"Wan generation needs at least {self.min_free_ram_gb} GB. "
                        "Close other apps or increase swap, then retry."
                    )
        except FileNotFoundError:
            return
        except Exception:
            return
