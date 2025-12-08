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
            enqueue=False  # Avoid multiprocessing semaphores (permission errors in some envs)
        )

        # Verbose debug sink for crash forensics (plain .txt for easy sharing)
        logger.add(
            "logs/debug.txt",
            rotation=f"{config.logging['max_size_mb']} MB",
            retention=config.logging['backup_count'],
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            backtrace=True,
            diagnose=True,
            enqueue=False,           # keep synchronous
            buffering=1,             # line-buffered; flush each entry
            mode="a"                 # append so crashes are preserved
        )

        # Separate upload log
        logger.add(
            "logs/upload.log",
            rotation=f"{config.logging['max_size_mb']} MB",
            retention=config.logging['backup_count'],
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
            filter=lambda record: "upload" in record["message"].lower(),
            enqueue=False
        )

    _install_exception_hook()
    return logger


def _install_exception_hook():
    """
    Capture uncaught exceptions and write full tracebacks to the debug log.
    """
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow clean Ctrl+C without noisy tracebacks
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).critical(
            "Uncaught exception - see logs/debug.txt for details"
        )

    sys.excepthook = handle_exception
