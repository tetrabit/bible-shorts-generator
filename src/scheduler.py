"""Scheduler for automated video generation and upload"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import pytz

from .config import config
from .utils.logger import setup_logger

logger = setup_logger(config)


def start_scheduler(generator):
    """
    Start the APScheduler for automated generation and upload

    Args:
        generator: BibleShortsGenerator instance
    """
    scheduler = BlockingScheduler(timezone=pytz.timezone(config.youtube['upload_schedule']['timezone']))

    # Generation job - runs at interval
    if config.scheduler['enabled']:
        interval_hours = int(config.scheduler['generation_interval'].rstrip('h'))

        @scheduler.scheduled_job(
            IntervalTrigger(hours=interval_hours),
            id='generate_videos',
            name='Generate video batch'
        )
        def generate_job():
            logger.info("===== STARTING SCHEDULED VIDEO GENERATION =====")
            try:
                batch_size = config.scheduler['batch_size']
                result = generator.run_batch(batch_size)
                logger.info(f"Generation complete: {result['successful']} successful, {result['failed']} failed")
            except Exception as e:
                logger.error(f"Generation job failed: {str(e)}")
            logger.info("===== GENERATION JOB COMPLETE =====\n")

    # Upload jobs - run at configured times
    if config.youtube['upload_schedule']['enabled']:
        for upload_time in config.youtube['upload_schedule']['times']:
            hour, minute = map(int, upload_time.split(':'))

            # Create a unique function for each schedule
            def make_upload_job(time_str):
                def upload_job():
                    logger.info(f"===== STARTING SCHEDULED UPLOAD ({time_str}) =====")
                    try:
                        # Get next video ready to upload
                        video_id = generator.db.get_next_to_upload()
                        if video_id:
                            logger.info(f"Uploading video ID: {video_id}")
                            generator.upload_video(video_id)
                        else:
                            logger.warning("No videos ready to upload")
                    except Exception as e:
                        logger.error(f"Upload job failed: {str(e)}")
                    logger.info("===== UPLOAD JOB COMPLETE =====\n")
                return upload_job

            scheduler.add_job(
                make_upload_job(upload_time),
                CronTrigger(hour=hour, minute=minute),
                id=f'upload_video_{upload_time}',
                name=f'Upload video at {upload_time}'
            )

    # Retry job - runs every 4 hours
    @scheduler.scheduled_job(
        IntervalTrigger(hours=4),
        id='retry_failed_videos',
        name='Retry failed videos'
    )
    def retry_job():
        logger.info("===== RUNNING RETRY JOB =====")
        try:
            result = generator.retry_failed_videos(max_retry_count=3)
            logger.info(f"Retry complete: {result['successful']} successful, {result['still_failed']} still failed")
        except Exception as e:
            logger.error(f"Retry job failed: {str(e)}")
        logger.info("===== RETRY JOB COMPLETE =====\n")

    # Cleanup job - runs daily at 3 AM
    @scheduler.scheduled_job(
        CronTrigger(hour=3, minute=0),
        id='cleanup_storage',
        name='Clean up old files'
    )
    def cleanup_job():
        logger.info("===== RUNNING STORAGE CLEANUP =====")
        try:
            from .utils.file_manager import cleanup_old_files, get_directory_size

            # Clean up old intermediate files
            if config.storage['cleanup_after_upload']:
                cleanup_old_files('generated/backgrounds', days=7)
                cleanup_old_files('generated/audio', days=7)
                cleanup_old_files('generated/timestamps', days=7)
                cleanup_old_files('generated/subtitles', days=7)

            # Check storage usage
            total_size = get_directory_size('generated')
            logger.info(f"Total storage usage: {total_size:.2f} GB")

            if total_size > config.storage['max_storage_gb']:
                logger.warning(f"Storage limit exceeded: {total_size:.2f} GB > {config.storage['max_storage_gb']} GB")
                # Clean up old uploaded videos
                cleanup_old_files('generated/uploaded', days=30)

            # Clean up old queue entries
            generator.db.cleanup_old_queue_entries(days=7)

        except Exception as e:
            logger.error(f"Cleanup job failed: {str(e)}")
        logger.info("===== CLEANUP JOB COMPLETE =====\n")

    # Database maintenance job - runs weekly on Sunday at 4 AM
    @scheduler.scheduled_job(
        CronTrigger(day_of_week='sun', hour=4, minute=0),
        id='database_maintenance',
        name='Database maintenance'
    )
    def database_maintenance():
        logger.info("===== RUNNING DATABASE MAINTENANCE =====")
        try:
            # Vacuum database
            import sqlite3
            conn = sqlite3.connect(generator.db.db_path)
            conn.execute("VACUUM")
            conn.close()
            logger.info("Database vacuumed successfully")
        except Exception as e:
            logger.error(f"Database maintenance failed: {str(e)}")
        logger.info("===== DATABASE MAINTENANCE COMPLETE =====\n")

    # Print scheduled jobs
    logger.info("Scheduler configured with the following jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} (ID: {job.id}, Next run: {job.next_run_time})")

    logger.info("\n" + "=" * 60)
    logger.info("SCHEDULER STARTED - Press Ctrl+C to exit")
    logger.info("=" * 60 + "\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\nScheduler stopped by user")
        scheduler.shutdown()
