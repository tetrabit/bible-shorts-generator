"""Text-to-Speech engine using Piper TTS"""
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from huggingface_hub import hf_hub_download


class TTSEngine:
    """Text-to-speech generator using Piper"""

    def __init__(self, config):
        self.config = config
        self.voice = config.models['tts']['voice']
        self.sample_rate = config.models['tts']['sample_rate']
        self.models_dir = Path("models/piper")
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, text: str, output_path: str) -> str:
        """
        Generate speech from text using Piper TTS

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file

        Returns:
            output_path: Path to generated audio file

        Raises:
            Exception: If TTS generation fails
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Ensure we have the voice model locally
        model_path, config_path = self._ensure_voice_downloaded()

        # Piper command
        cmd = [
            "piper",
            "--model", str(model_path),
            "--config", str(config_path),
            "--output_file", output_path
        ]

        try:
            # Pass text via stdin
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=text)

            if process.returncode != 0:
                raise Exception(f"Piper TTS failed: {stderr}")

            # Verify file was created
            if not Path(output_path).exists():
                raise Exception(f"Audio file not created: {output_path}")

            return output_path

        except FileNotFoundError:
            raise Exception(
                "Piper TTS not found. Install with: pip install piper-tts"
            )
        except Exception as e:
            raise Exception(f"TTS generation failed: {str(e)}")

    def _ensure_voice_downloaded(self) -> Tuple[Path, Path]:
        """
        Ensure the requested voice model and config are present locally.

        Returns:
            (model_path, config_path)
        """
        model_path, config_path = self._get_voice_paths()

        if model_path.exists() and config_path.exists():
            return model_path, config_path

        try:
            # Derive repository path for the voice inside rhasspy/piper-voices
            lang_code, speaker, quality = self._parse_voice_id()
            lang_prefix = lang_code.split("_")[0]
            base_path = f"{lang_prefix}/{lang_code}/{speaker}/{quality}"

            # Download model and config into a dedicated folder
            local_dir = model_path.parent
            local_dir.mkdir(parents=True, exist_ok=True)

            hf_hub_download(
                repo_id="rhasspy/piper-voices",
                filename=f"{base_path}/{self.voice}.onnx",
                local_dir=str(local_dir),
                local_dir_use_symlinks=False,
            )
            hf_hub_download(
                repo_id="rhasspy/piper-voices",
                filename=f"{base_path}/{self.voice}.onnx.json",
                local_dir=str(local_dir),
                local_dir_use_symlinks=False,
            )
        except Exception as e:
            raise Exception(
                f"Piper voice download failed for {self.voice}: {e}"
            )

        return model_path, config_path

    def _get_voice_paths(self) -> Tuple[Path, Path]:
        """Return the expected local paths for the voice model and config."""
        voice_dir = self.models_dir / self.voice
        model_path = voice_dir / f"{self.voice}.onnx"
        config_path = voice_dir / f"{self.voice}.onnx.json"
        return model_path, config_path

    def _parse_voice_id(self) -> Tuple[str, str, str]:
        """
        Parse a voice id like 'en_US-lessac-medium' into lang_code, speaker, quality.
        Falls back to reasonable defaults if parts are missing.
        """
        parts = self.voice.split("-")
        lang_code = parts[0] if parts else "en_US"
        speaker = parts[1] if len(parts) > 1 else "lessac"
        quality = parts[2] if len(parts) > 2 else "medium"
        return lang_code, speaker, quality

    def test_installation(self) -> bool:
        """Test if Piper is installed and working"""
        try:
            result = subprocess.run(
                ["piper", "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
