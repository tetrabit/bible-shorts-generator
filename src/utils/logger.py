"""Logging setup for Bible Shorts Generator"""
from loguru import logger
import sys
from pathlib import Path


def setup_logger(config):
    """
    Configure loguru logger based on config settings

    Args:
        config: Config object with logging settings

    Returns:
        logger: Configured loguru logger instance
    """
    # Remove default handler
    logger.remove()

    # Console output
    if config.logging['console']:
        logger.add(
            sys.stdout,
            level=config.logging['level'],
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            colorize=True
        )

    # File output
    if config.logging['file']:
        # Ensure logs directory exists
        Path("logs").mkdir(exist_ok=True)

        logger.add(
            "logs/app.log",
            rotation=f"{config.logging['max_size_mb']} MB",
            retention=config.logging['backup_count'],
            level=config.logging['level'],
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            enqueue=True  # Thread-safe logging
        )

        # Separate upload log
        logger.add(
            "logs/upload.log",
            rotation=f"{config.logging['max_size_mb']} MB",
            retention=config.logging['backup_count'],
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
            filter=lambda record: "upload" in record["message"].lower(),
            enqueue=True
        )

    return logger
