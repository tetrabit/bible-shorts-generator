"""Text-to-video generator using Qwen3-VL (placeholder integration)."""
import subprocess
from pathlib import Path
from typing import Optional

import numpy as np
import cv2


class QwenVideoGenerator:
    """
    Minimal integration point for Qwen3-VL text-to-video.
    Currently expects a local Qwen3-VL checkout; falls back to a placeholder
    video if the model/tooling is not available.
    """

    def __init__(self, config, fallback=None):
        self.config = config
        self.repo_dir = Path(config.models['qwen3']['repo_dir'])
        self.max_duration = config.models['qwen3'].get('max_duration', 6)
        self.fallback = fallback  # Optional VideoGenerator for fallback (unused when strict mode)

    def is_available(self) -> bool:
        """
        Return True if a Qwen3-VL checkout exists locally and importable.
        """
        if not (self.repo_dir.exists() and (self.repo_dir / "README.md").exists()):
            return False
        try:
            __import__("qwen3_vl")
            return True
        except Exception:
            return False

    def generate(self, prompt: str, duration: float, output_path: str) -> str:
        """
        Generate a background video from text using Qwen3-VL.

        If Qwen3-VL is not available, optionally fall back to the provided
        fallback generator or emit a placeholder clip.
        """
        if duration > self.max_duration:
            duration = self.max_duration

        if not self.is_available():
            raise RuntimeError(
                "Qwen3-VL not available. Clone the repo and install its dependencies "
                f"at {self.repo_dir}, then retry."
            )

        # Placeholder command invocation; replace with actual Qwen3-VL inference as needed.
        cmd = [
            "python",
            "-m",
            "qwen3_vl.generate_video",
            "--text",
            prompt,
            "--output",
            output_path,
            "--duration",
            str(duration),
        ]
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Qwen3-VL generation failed: {result.stderr}"
            )
        if not Path(output_path).exists():
            raise RuntimeError(
                f"Qwen3-VL did not produce output at {output_path}"
            )
        return output_path

    def _generate_placeholder(self, duration: float, output_path: str) -> str:
        """Generate a simple colored placeholder video."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fps = self.config.video['fps']
        total_frames = int(duration * fps)
        width = self.config.video['width']
        height = self.config.video['height']

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not writer.isOpened():
            raise RuntimeError(f"Failed to open placeholder writer at {output_path}")

        base_color = np.array([60, 50, 200], dtype=np.uint8)  # BGR
        for _ in range(total_frames):
            frame = np.tile(base_color, (height, width, 1))
            writer.write(frame)

        writer.release()
        return output_path
