"""
Centralized multi-file logging system.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from Core.config import config

LOG_DIR = Path(__file__).resolve().parent.parent / config.logging.dir
LOG_DIR.mkdir(parents=True, exist_ok=True)

class LogManager:
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, log_file: str = "system.log") -> logging.Logger:
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console_level = getattr(logging, config.logging.level_console.upper(), logging.INFO)
        console.setLevel(console_level)
        console.setFormatter(logging.Formatter(
            "%(asctime)s │ %(name)-15s │ %(levelname)-7s │ %(message)s",
            datefmt="%H:%M:%S"
        ))

        # File handler
        today = datetime.now().strftime('%Y%m%d')
        # Insert date before extension
        file_parts = log_file.split('.')
        dated_file = f"{file_parts[0]}_{today}.{file_parts[1]}" if len(file_parts) == 2 else f"{log_file}_{today}.log"
        
        file_path = LOG_DIR / dated_file
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_level = getattr(logging, config.logging.level_file.upper(), logging.DEBUG)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s │ %(name)-15s │ %(levelname)-7s │ %(funcName)s:%(lineno)d │ %(message)s"
        ))

        logger.addHandler(console)
        logger.addHandler(file_handler)

        cls._loggers[name] = logger
        return logger

# Convenience methods for specific log files
def get_audio_logger(name="audio"):
    return LogManager.get_logger(name, "audio.log")

def get_ai_logger(name="ai"):
    return LogManager.get_logger(name, "ai.log")

def get_error_logger(name="error"):
    return LogManager.get_logger(name, "error.log")

def get_system_logger(name="system"):
    return LogManager.get_logger(name, "system.log")
