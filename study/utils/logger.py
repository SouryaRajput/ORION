"""
Centralized logging for the Study Mode system.
All modules use this logger for consistent formatting and file output.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "study"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Create a module-specific logger with console + file output."""
    logger = logging.getLogger(f"study.{name}")

    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # Console handler — INFO level, clean format
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S"
    ))

    # File handler — DEBUG level, full detail
    log_file = LOG_DIR / f"study_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s │ %(name)s │ %(levelname)s │ %(funcName)s:%(lineno)d │ %(message)s"
    ))

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger
