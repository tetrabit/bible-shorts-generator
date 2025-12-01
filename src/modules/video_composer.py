"""Video composer for final assembly using FFmpeg"""
from pathlib import Path
from ..utils.ffmpeg_utils import run_ffmpeg


class VideoComposer:
    """Composes final video from background, audio, and subtitles"""

    def __init__(self, config):
        self.config = config

    def compose(
        self,
        background_path: str,
        audio_path: str,
        subtitle_path: str,
        output_path: str
    ) -> str:
        """
        Compose final video using FFmpeg

        Args:
            background_path: Path to background video
            audio_path: Path to audio file
            subtitle_path: Path to subtitle overlay video
            output_path: Path to save final video

        Returns:
            output_path: Path to saved video
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        print("Composing final video...")

        # FFmpeg command to overlay subtitles and add audio
        args = [
            "-i", background_path,        # Input 0: Background video
            "-i", subtitle_path,           # Input 1: Subtitle overlay
            "-i", audio_path,              # Input 2: Audio
            "-filter_complex",
            "[0:v][1:v]overlay=0:0:format=auto[outv]",  # Overlay subtitles on background
            "-map", "[outv]",              # Use overlaid video
            "-map", "2:a",                 # Use audio from third input
            "-c:v", self.config.video['codec'],
            "-preset", self.config.video['preset'],
            "-crf", str(self.config.video['crf']),
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",                   # End at shortest input
            "-movflags", "+faststart",     # Enable fast start for web
            "-y",                          # Overwrite output
            output_path
        ]

        run_ffmpeg(args, "Video composition")
        print(f"Final video saved to: {output_path}")

        return output_path

    def compose_simple(
        self,
        video_path: str,
        audio_path: str,
        output_path: str
    ) -> str:
        """
        Simple composition: just add audio to video

        Args:
            video_path: Path to video file
            audio_path: Path to audio file
            output_path: Path to save output

        Returns:
            output_path: Path to saved video
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        args = [
            "-i", video_path,
            "-i", audio_path,
            "-c:v", self.config.video['codec'],
            "-preset", self.config.video['preset'],
            "-crf", str(self.config.video['crf']),
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            "-y",
            output_path
        ]

        run_ffmpeg(args, "Simple video composition")
        return output_path
