"""Text-to-Speech engine using Piper TTS"""
import subprocess
from pathlib import Path
from typing import Optional


class TTSEngine:
    """Text-to-speech generator using Piper"""

    def __init__(self, config):
        self.config = config
        self.voice = config.models['tts']['voice']
        self.sample_rate = config.models['tts']['sample_rate']

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

        # Piper command
        cmd = [
            "piper",
            "--model", self.voice,
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
