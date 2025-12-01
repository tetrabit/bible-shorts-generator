#!/usr/bin/env python3
"""
Bible Shorts Generator - Main Orchestrator
Automated system for creating YouTube Shorts from Bible verses
"""
import sys
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.utils.logger import setup_logger
from src.modules.database import Database
from src.modules.verse_selector import VerseSelector
from src.modules.timing_analyzer import TimingAnalyzer
from src.modules.video_generator import VideoGenerator
from src.modules.tts_engine import TTSEngine
from src.modules.word_aligner import WordAligner
from src.modules.subtitle_renderer import SubtitleRenderer
from src.modules.video_composer import VideoComposer
from src.modules.youtube_uploader import YouTubeUploader
from src.utils.file_manager import archive_video, cleanup_intermediate_files

console = Console()
logger = setup_logger(config)


class BibleShortsGenerator:
    """Main orchestrator for Bible Shorts generation pipeline"""

    def __init__(self):
        logger.info("Initializing Bible Shorts Generator...")

        # Initialize components
        self.config = config
        self.db = Database()
        self.verse_selector = VerseSelector(config, self.db)
        self.timing = TimingAnalyzer(config)
        self.video_gen = VideoGenerator(config)
        self.tts = TTSEngine(config)
        self.aligner = WordAligner(config)
        self.subtitle_renderer = SubtitleRenderer(config)
        self.composer = VideoComposer(config)
        self.uploader = None  # Lazy load

        logger.info("Initialization complete!")

    def _init_uploader(self):
        """Initialize YouTube uploader (lazy)"""
        if self.uploader is None:
            self.uploader = YouTubeUploader(config)

    def generate_video(self, verse=None):
        """
        Generate a complete video from verse to final output

        Args:
            verse: Optional verse data (if None, will select random verse)

        Returns:
            dict: Video generation result
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:

            # Step 1: Select verse
            task = progress.add_task("Selecting verse...", total=None)
            if not verse:
                verse = self.verse_selector.select_verse()
                if not verse:
                    logger.error("No suitable verse found")
                    console.print("[red]ERROR: No suitable verse found. Try adjusting word count limits.[/red]")
                    return None
            progress.update(task, completed=100)

            logger.info(f"Selected: {verse['reference']} - {verse['text']}")
            console.print(f"\n[bold cyan]Selected Verse:[/bold cyan] {verse['reference']}")
            console.print(f"[italic]{verse['text']}[/italic]")
            console.print(f"Words: {verse['word_count']}, Duration: {verse['duration']}s\n")

            # Create video record in database
            video_id = self.db.add_video(verse)
            self.db.update_video_status(video_id, 'processing')

            # Define output paths
            paths = {
                'background': f"generated/backgrounds/{verse['id']}.mp4",
                'audio': f"generated/audio/{verse['id']}.wav",
                'timestamps': f"generated/timestamps/{verse['id']}.json",
                'subtitles': f"generated/subtitles/{verse['id']}.webm",
                'final': f"generated/final/{verse['id']}.mp4"
            }

            try:
                # Step 2: Generate background video
                task = progress.add_task("Generating background video...", total=None)
                self.video_gen.generate(
                    verse['text'],
                    verse['duration'],
                    paths['background']
                )
                self.db.update_video_path(video_id, 'background_path', paths['background'])
                progress.update(task, completed=100)

                # Step 3: Generate TTS audio
                task = progress.add_task("Generating speech...", total=None)
                self.tts.generate(verse['text'], paths['audio'])
                self.db.update_video_path(video_id, 'audio_path', paths['audio'])
                progress.update(task, completed=100)

                # Step 4: Extract word timestamps
                task = progress.add_task("Extracting word timings...", total=None)
                try:
                    self.aligner.align(
                        paths['audio'],
                        verse['text'],
                        paths['timestamps']
                    )
                finally:
                    # Free WhisperX models from GPU/CPU memory between videos
                    self.aligner.unload_models()

                self.db.update_video_path(video_id, 'timestamps_path', paths['timestamps'])
                progress.update(task, completed=100)

                # Step 5: Render subtitles (skip in debug mode)
                if not self.config.video.get('skip_subtitles', False):
                    task = progress.add_task("Rendering subtitles...", total=None)
                    self.subtitle_renderer.create_subtitle_video(
                        paths['timestamps'],
                        verse['duration'],
                        paths['subtitles']
                    )
                    self.db.update_video_path(video_id, 'subtitle_path', paths['subtitles'])
                    progress.update(task, completed=100)

                # Step 6: Compose final video
                task = progress.add_task("Composing final video...", total=None)
                if self.config.video.get('skip_subtitles', False):
                    self.composer.compose_simple(
                        paths['background'],
                        paths['audio'],
                        paths['final']
                    )
                else:
                    self.composer.compose(
                        paths['background'],
                        paths['audio'],
                        paths['subtitles'],
                        paths['final']
                    )
                self.db.update_video_path(video_id, 'final_path', paths['final'])
                self.db.update_video_status(video_id, 'ready')
                progress.update(task, completed=100)

                logger.info(f"Video generated successfully: {paths['final']}")
                console.print(f"\n[green]✓ Video generated successfully![/green]")
                console.print(f"File: {paths['final']}\n")

                # Update statistics
                self.db.update_statistics(
                    videos_generated=1,
                    total_duration=verse['duration']
                )

                return {
                    'video_id': video_id,
                    'path': paths['final'],
                    'verse': verse
                }

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Video generation failed: {error_msg}")
                self.db.mark_video_failed(video_id, error_msg)
                self.db.update_statistics(errors=1)
                console.print(f"\n[red]ERROR: Video generation failed - {error_msg}[/red]\n")
                return None

    def upload_video(self, video_id: int):
        """
        Upload a generated video to YouTube

        Args:
            video_id: Database ID of video to upload

        Returns:
            dict: Upload result
        """
        self._init_uploader()

        video = self.db.get_video(video_id)
        if not video:
            logger.error(f"Video ID {video_id} not found")
            console.print(f"[red]ERROR: Video ID {video_id} not found[/red]")
            return None

        if video['status'] != 'ready':
            logger.error(f"Video {video_id} is not ready for upload (status: {video['status']})")
            console.print(f"[red]ERROR: Video not ready for upload[/red]")
            return None

        logger.info(f"Uploading video {video_id} to YouTube...")
        console.print(f"\n[bold]Uploading to YouTube...[/bold]")

        try:
            # Reconstruct verse data from database
            verse_data = {
                'reference': f"{video['book']} {video['chapter']}:{video['verse']}",
                'text': video['text']
            }

            result = self.uploader.upload(
                video['final_path'],
                verse_data
            )

            self.db.update_video_upload(
                video_id,
                result['id'],
                result['url']
            )

            logger.info(f"Upload complete: {result['url']}")
            console.print(f"[green]✓ Upload successful![/green]")
            console.print(f"URL: {result['url']}\n")

            # Archive video if configured
            if config.storage['archive_uploaded']:
                archive_video(video['verse_id'])

            # Cleanup intermediate files if configured
            if config.storage['cleanup_after_upload']:
                cleanup_intermediate_files(
                    video['verse_id'],
                    keep_final=config.storage['keep_final_videos']
                )

            # Update statistics
            self.db.update_statistics(videos_uploaded=1)

            return result

        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            self.db.update_statistics(errors=1)
            console.print(f"[red]ERROR: Upload failed - {str(e)}[/red]\n")
            return None

    def run_batch(self, count: int = 1):
        """
        Generate and queue multiple videos

        Args:
            count: Number of videos to generate
        """
        console.print(f"\n[bold blue]Starting batch generation of {count} videos...[/bold blue]\n")

        successful = 0
        failed = 0

        for i in range(count):
            console.print(f"\n[bold]--- Video {i+1}/{count} ---[/bold]")

            result = self.generate_video()

            if result:
                successful += 1
            else:
                failed += 1

        console.print(f"\n[bold green]Batch generation complete![/bold green]")
        console.print(f"Successful: {successful}, Failed: {failed}\n")

        return {'successful': successful, 'failed': failed}

    def retry_failed_videos(self, max_retry_count: int = 3):
        """
        Retry generating failed videos

        Args:
            max_retry_count: Maximum number of retries per video

        Returns:
            dict: Results of retry attempts
        """
        failed_videos = self.db.get_failed_videos_for_retry(max_retry_count)

        if not failed_videos:
            console.print("[yellow]No failed videos eligible for retry[/yellow]")
            return {'retried': 0, 'successful': 0, 'still_failed': 0}

        console.print(f"\n[bold blue]Retrying {len(failed_videos)} failed videos...[/bold blue]\n")

        retried = 0
        successful = 0
        still_failed = 0

        for video in failed_videos:
            console.print(f"\n[bold]Retrying: {video['verse_id']}[/bold]")
            console.print(f"Previous error: {video['error_message']}")
            console.print(f"Retry attempt: {video['retry_count'] + 1}/{max_retry_count}")

            # Reset video to pending
            self.db.reset_video_for_retry(video['id'])

            # Reconstruct verse data
            verse_data = {
                'id': video['verse_id'],
                'book': video['book'],
                'chapter': video['chapter'],
                'verse': video['verse'],
                'reference': f"{video['book']} {video['chapter']}:{video['verse']}",
                'text': video['text'],
                'word_count': video['word_count'],
                'duration': video['duration']
            }

            # Try to regenerate
            result = self.generate_video(verse=verse_data)

            retried += 1
            if result:
                successful += 1
                console.print(f"[green]✓ Retry successful![/green]")
            else:
                still_failed += 1
                console.print(f"[red]✗ Retry failed[/red]")

        console.print(f"\n[bold green]Retry complete![/bold green]")
        console.print(f"Total retried: {retried}")
        console.print(f"Successful: {successful}")
        console.print(f"Still failed: {still_failed}\n")

        return {
            'retried': retried,
            'successful': successful,
            'still_failed': still_failed
        }


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Bible Shorts Generator - Automated YouTube Shorts creator"
    )
    parser.add_argument(
        '--generate',
        type=int,
        metavar='N',
        help='Generate N videos'
    )
    parser.add_argument(
        '--upload',
        type=int,
        metavar='ID',
        help='Upload video by database ID'
    )
    parser.add_argument(
        '--schedule',
        action='store_true',
        help='Start scheduler for automated generation and upload'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics'
    )
    parser.add_argument(
        '--retry',
        action='store_true',
        help='Retry failed videos'
    )
    parser.add_argument(
        '--mode',
        choices=['random', 'sequential'],
        help='Set verse selection mode'
    )
    parser.add_argument(
        '--progress',
        action='store_true',
        help='Show current progress (for sequential mode)'
    )

    args = parser.parse_args()

    # Create generator
    generator = BibleShortsGenerator()

    if args.generate:
        generator.run_batch(args.generate)

    elif args.upload:
        generator.upload_video(args.upload)

    elif args.schedule:
        from src.scheduler import start_scheduler
        start_scheduler(generator)

    elif args.stats:
        stats = generator.db.get_statistics(days=7)
        status_counts = generator.db.get_video_count_by_status()
        processing_stats = generator.db.get_processing_stats()
        progress = generator.db.get_progress()

        console.print("\n[bold]Statistics (Last 7 Days)[/bold]")
        console.print("=" * 50)
        for stat in stats:
            console.print(f"Date: {stat['date']}")
            console.print(f"  Generated: {stat['videos_generated']}")
            console.print(f"  Uploaded: {stat['videos_uploaded']}")
            console.print(f"  Errors: {stat['errors']}")
            console.print()

        console.print("[bold]Video Status Counts[/bold]")
        console.print("=" * 50)
        for status, count in status_counts.items():
            console.print(f"{status}: {count}")
        console.print()

        console.print("[bold]Processing Stats[/bold]")
        console.print("=" * 50)
        console.print(f"Total videos: {processing_stats.get('total', 0)}")
        console.print(f"Failed (retryable): {processing_stats.get('retryable', 0)}")
        console.print(f"Failed (permanent): {processing_stats.get('permanently_failed', 0)}")
        console.print()

        console.print("[bold]Current Mode[/bold]")
        console.print("=" * 50)
        console.print(f"Mode: {progress.get('mode', 'random')}")
        if progress.get('mode') == 'sequential' and progress.get('current_book'):
            console.print(f"Progress: {progress['current_book']} {progress['current_chapter']}:{progress['current_verse']}")
        console.print()

    elif args.retry:
        generator.retry_failed_videos()

    elif args.mode:
        generator.db.set_mode(args.mode)
        console.print(f"[green]✓ Mode set to: {args.mode}[/green]")
        if args.mode == 'sequential':
            console.print("\n[yellow]Sequential mode will process verses in order from configured books.[/yellow]")
            console.print("[yellow]Progress will be saved and resumed after shutdown.[/yellow]\n")

    elif args.progress:
        progress = generator.db.get_progress()
        processing_stats = generator.db.get_processing_stats()

        console.print("\n[bold]Current Progress[/bold]")
        console.print("=" * 50)
        console.print(f"Mode: {progress.get('mode', 'random')}")

        if progress.get('mode') == 'sequential':
            if progress.get('current_book'):
                console.print(f"Current position: {progress['current_book']} {progress['current_chapter']}:{progress['current_verse']}")
                console.print(f"Last updated: {progress.get('updated_at', 'N/A')}")
            else:
                console.print("Not started yet")
        else:
            console.print("Random mode - no sequential progress tracked")

        console.print()
        console.print(f"Total verses processed: {processing_stats.get('total', 0)}")
        console.print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
