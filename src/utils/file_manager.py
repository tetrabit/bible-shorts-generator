"""File management utilities"""
from pathlib import Path
import shutil
from typing import Dict, List
import os


def cleanup_old_files(directory: str, days: int = 7, pattern: str = "*"):
    """
    Clean up files older than specified days

    Args:
        directory: Directory to clean
        days: Age threshold in days
        pattern: File pattern to match
    """
    import time

    dir_path = Path(directory)
    if not dir_path.exists():
        return

    current_time = time.time()
    age_threshold = days * 86400  # Convert days to seconds

    for file_path in dir_path.glob(pattern):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > age_threshold:
                file_path.unlink()
                print(f"Deleted old file: {file_path}")


def get_directory_size(directory: str) -> float:
    """
    Get total size of directory in GB

    Args:
        directory: Directory path

    Returns:
        size_gb: Size in gigabytes
    """
    total_size = 0
    dir_path = Path(directory)

    if not dir_path.exists():
        return 0.0

    for file_path in dir_path.rglob('*'):
        if file_path.is_file():
            total_size += file_path.stat().st_size

    return total_size / (1024 ** 3)  # Convert to GB


def ensure_directory(path: str):
    """Ensure directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)


def move_file(source: str, destination: str):
    """Move file to destination"""
    ensure_directory(str(Path(destination).parent))
    shutil.move(source, destination)


def copy_file(source: str, destination: str):
    """Copy file to destination"""
    ensure_directory(str(Path(destination).parent))
    shutil.copy2(source, destination)


def delete_file(path: str):
    """Delete file if it exists"""
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()


def list_files(directory: str, pattern: str = "*", recursive: bool = False) -> List[str]:
    """
    List files in directory

    Args:
        directory: Directory to search
        pattern: File pattern to match
        recursive: Search recursively

    Returns:
        List of file paths
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    if recursive:
        files = dir_path.rglob(pattern)
    else:
        files = dir_path.glob(pattern)

    return [str(f) for f in files if f.is_file()]


def cleanup_intermediate_files(video_id: int, keep_final: bool = True):
    """
    Clean up intermediate files for a video

    Args:
        video_id: Video ID
        keep_final: Whether to keep the final video
    """
    # Define paths to clean
    paths_to_clean = [
        f"generated/backgrounds/{video_id}.mp4",
        f"generated/audio/{video_id}.wav",
        f"generated/timestamps/{video_id}.json",
        f"generated/subtitles/{video_id}.mp4"
    ]

    if not keep_final:
        paths_to_clean.append(f"generated/final/{video_id}.mp4")

    for path in paths_to_clean:
        delete_file(path)


def archive_video(video_id: int):
    """Move final video to uploaded archive"""
    source = f"generated/final/{video_id}.mp4"
    destination = f"generated/uploaded/{video_id}.mp4"

    if Path(source).exists():
        move_file(source, destination)


def check_disk_space(path: str = ".") -> Dict[str, float]:
    """
    Check available disk space

    Args:
        path: Path to check

    Returns:
        dict: total, used, free space in GB
    """
    stat = shutil.disk_usage(path)

    return {
        'total_gb': stat.total / (1024 ** 3),
        'used_gb': stat.used / (1024 ** 3),
        'free_gb': stat.free / (1024 ** 3),
        'percent_used': (stat.used / stat.total) * 100
    }
