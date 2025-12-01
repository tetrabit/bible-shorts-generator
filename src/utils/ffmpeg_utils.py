"""FFmpeg utility functions"""
import subprocess
from pathlib import Path
from typing import List, Optional


def run_ffmpeg(args: List[str], description: str = "FFmpeg operation") -> bool:
    """
    Run FFmpeg command

    Args:
        args: List of FFmpeg arguments
        description: Description of operation for error messages

    Returns:
        bool: True if successful

    Raises:
        Exception: If FFmpeg fails
    """
    cmd = ["ffmpeg"] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            raise Exception(
                f"{description} failed:\n{result.stderr}"
            )

        return True

    except FileNotFoundError:
        raise Exception("FFmpeg not found. Install with: sudo apt-get install ffmpeg")
    except Exception as e:
        raise Exception(f"{description} error: {str(e)}")


def check_ffmpeg() -> bool:
    """Check if FFmpeg is installed"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_video_duration(video_path: str) -> Optional[float]:
    """Get video duration in seconds"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return None


def get_video_resolution(video_path: str) -> Optional[tuple]:
    """Get video resolution as (width, height)"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        width, height = result.stdout.strip().split('x')
        return (int(width), int(height))
    except Exception:
        return None


def convert_images_to_video(
    images: List[str],
    output_path: str,
    fps: int = 30,
    duration: float = None
) -> str:
    """
    Convert list of images to video

    Args:
        images: List of image file paths
        output_path: Output video path
        fps: Frames per second
        duration: Total duration (if None, uses 1 second per image)

    Returns:
        output_path: Path to created video
    """
    # Create temporary file list
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for img in images:
            f.write(f"file '{img}'\n")
            if duration:
                f.write(f"duration {duration / len(images)}\n")
        file_list = f.name

    try:
        args = [
            "-f", "concat",
            "-safe", "0",
            "-i", file_list,
            "-vf", f"fps={fps}",
            "-pix_fmt", "yuv420p",
            "-y",
            output_path
        ]
        run_ffmpeg(args, "Image to video conversion")
        return output_path
    finally:
        Path(file_list).unlink(missing_ok=True)


def overlay_videos(
    background: str,
    overlay: str,
    output_path: str,
    audio_path: Optional[str] = None
) -> str:
    """
    Overlay one video on top of another

    Args:
        background: Background video path
        overlay: Overlay video path (with transparency)
        output_path: Output video path
        audio_path: Optional audio file to add

    Returns:
        output_path: Path to created video
    """
    inputs = ["-i", background, "-i", overlay]
    filter_complex = "[0:v][1:v]overlay=0:0[outv]"
    map_args = ["-map", "[outv]"]

    # Add audio if provided
    if audio_path:
        inputs.extend(["-i", audio_path])
        map_args.extend(["-map", "2:a"])

    args = inputs + [
        "-filter_complex", filter_complex
    ] + map_args + [
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-y",
        output_path
    ]

    run_ffmpeg(args, "Video overlay")
    return output_path


def add_audio_to_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    shortest: bool = True
) -> str:
    """
    Add audio track to video

    Args:
        video_path: Input video path
        audio_path: Audio file path
        output_path: Output video path
        shortest: End output at shortest input

    Returns:
        output_path: Path to created video
    """
    args = [
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k"
    ]

    if shortest:
        args.append("-shortest")

    args.extend(["-y", output_path])

    run_ffmpeg(args, "Add audio to video")
    return output_path


def trim_video(
    video_path: str,
    output_path: str,
    start: float = 0,
    duration: Optional[float] = None
) -> str:
    """
    Trim video to specific duration

    Args:
        video_path: Input video path
        output_path: Output video path
        start: Start time in seconds
        duration: Duration in seconds (None for end of video)

    Returns:
        output_path: Path to created video
    """
    args = ["-i", video_path, "-ss", str(start)]

    if duration:
        args.extend(["-t", str(duration)])

    args.extend([
        "-c", "copy",
        "-y",
        output_path
    ])

    run_ffmpeg(args, "Trim video")
    return output_path
