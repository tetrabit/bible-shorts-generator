"""Subtitle renderer with word-level highlighting"""
import json
from pathlib import Path
from typing import List, Dict, Tuple

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from loguru import logger
import shutil
import tempfile
from ..utils.ffmpeg_utils import run_ffmpeg


class SubtitleRenderer:
    """Renders subtitle overlays with word-by-word highlighting"""

    def __init__(self, config):
        self.config = config
        self.font = self._load_font()

    def _load_font(self) -> ImageFont.FreeTypeFont:
        """Load font for subtitles, downloading if missing."""
        font_path = Path(self.config.text['font_path'])

        if not font_path.exists():
            logger.warning(f"Configured font not found at {font_path}. Attempting download...")
            font_path = self._download_font(font_path)

        try:
            return ImageFont.truetype(str(font_path), self.config.text['font_size'])
        except Exception as exc:
            logger.error(f"Failed to load font at {font_path}: {exc}. Falling back to default font.")
            return ImageFont.load_default()

    def _download_font(self, target_path: Path) -> Path:
        """
        Download a fallback DejaVuSans-Bold font if the configured font is missing.
        The downloaded file is saved to the specified target path.
        """
        # Use DejaVuSans-Bold as a permissive default
        url = "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/version_2_37/ttf/DejaVuSans-Bold.ttf"
        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            target_path.write_bytes(resp.content)
            logger.info(f"Downloaded fallback font to {target_path}")
        except Exception as exc:
            logger.error(f"Failed to download fallback font from {url}: {exc}")
        return target_path

    def get_current_words(self, words: List[Dict], time: float, window: int = 3) -> Tuple[List[str], int]:
        """
        Get words to display at given time with highlight index

        Args:
            words: List of word dictionaries with timestamps
            time: Current time in seconds
            window: Number of words to show at once

        Returns:
            (words_to_show, highlight_index): Words to display and which to highlight
        """
        # Find currently spoken word
        current_idx = None
        for idx, word in enumerate(words):
            if word['start'] <= time <= word['end']:
                current_idx = idx
                break

        if current_idx is None:
            # Find nearest word
            for idx, word in enumerate(words):
                if word['start'] > time:
                    current_idx = max(0, idx - 1)
                    break
            if current_idx is None:
                current_idx = len(words) - 1

        # Get window of words centered on current
        start_idx = max(0, current_idx - window // 2)
        end_idx = min(len(words), start_idx + window)

        # Adjust start if we're near the end
        if end_idx - start_idx < window:
            start_idx = max(0, end_idx - window)

        words_to_show = [w['word'] for w in words[start_idx:end_idx]]
        highlight_idx = current_idx - start_idx

        return words_to_show, highlight_idx

    def render_frame(
        self,
        words: List[str],
        highlight_idx: int,
        width: int,
        height: int
    ) -> np.ndarray:
        """
        Render a single subtitle frame

        Args:
            words: List of words to display
            highlight_idx: Index of word to highlight
            width: Frame width
            height: Frame height

        Returns:
            numpy array: RGBA image
        """
        # Create transparent image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Join words for layout calculation
        text = " ".join(words)

        # Calculate text position
        try:
            bbox = draw.textbbox((0, 0), text, font=self.font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception:
            # Fallback for older PIL versions
            text_width, text_height = draw.textsize(text, font=self.font)

        # Position based on config
        x = (width - text_width) // 2
        if self.config.text['position'] == 'bottom':
            y = height - text_height - self.config.text['padding_bottom']
        elif self.config.text['position'] == 'top':
            y = self.config.text['padding_bottom']
        else:  # center
            y = (height - text_height) // 2

        # Draw each word with appropriate color
        current_x = x
        outline_width = self.config.text['outline_width']

        for idx, word in enumerate(words):
            # Determine color
            if idx == highlight_idx:
                color = tuple(self.config.text['highlight_color']) + (255,)
            else:
                color = tuple(self.config.text['font_color']) + (255,)

            # Draw outline
            outline_color = tuple(self.config.text['outline_color']) + (255,)
            for adj_x in range(-outline_width, outline_width + 1):
                for adj_y in range(-outline_width, outline_width + 1):
                    if adj_x != 0 or adj_y != 0:
                        draw.text(
                            (current_x + adj_x, y + adj_y),
                            word,
                            font=self.font,
                            fill=outline_color
                        )

            # Draw main text
            draw.text((current_x, y), word, font=self.font, fill=color)

            # Update x position
            try:
                word_bbox = draw.textbbox((0, 0), word + " ", font=self.font)
                word_width = word_bbox[2] - word_bbox[0]
            except Exception:
                word_width, _ = draw.textsize(word + " ", font=self.font)

            current_x += word_width

        return np.array(img)

    def create_subtitle_video(
        self,
        timestamps_path: str,
        duration: float,
        output_path: str
    ) -> str:
        """
        Create full subtitle overlay video

        Args:
            timestamps_path: Path to timestamps JSON file
            duration: Total video duration
            output_path: Path to save subtitle video

        Returns:
            output_path: Path to saved video
        """
        # Load timestamps
        with open(timestamps_path) as f:
            words = json.load(f)

        if not words:
            raise ValueError("No words found in timestamps file")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        fps = self.config.video['fps']
        total_frames = int(duration * fps)

        tmp_dir = Path(tempfile.mkdtemp(prefix="subs_frames_"))
        try:
            print(f"Rendering {total_frames} frames of subtitles...")

            for frame_idx in range(total_frames):
                time = frame_idx / fps

                # Get words to display
                words_to_show, highlight_idx = self.get_current_words(words, time)

                # Render frame
                frame = self.render_frame(
                    words_to_show,
                    highlight_idx,
                    self.config.video['width'],
                    self.config.video['height']
                )

                frame_path = tmp_dir / f"frame_{frame_idx:05d}.png"
                Image.fromarray(frame, mode="RGBA").save(frame_path)

                if (frame_idx + 1) % 30 == 0:
                    print(f"Rendered {frame_idx + 1}/{total_frames} frames")

            # Encode frames to MOV with alpha (qtrle) for reliable overlay
            output_mov = str(Path(output_path).with_suffix(".mov"))
            ffmpeg_args = [
                "-framerate", str(fps),
                "-i", str(tmp_dir / "frame_%05d.png"),
                "-c:v", "qtrle",
                "-pix_fmt", "argb",
                "-y",
                output_mov
            ]
            run_ffmpeg(ffmpeg_args, "Subtitle encoding")
            print(f"Subtitle video saved to: {output_mov}")
            return output_mov
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
