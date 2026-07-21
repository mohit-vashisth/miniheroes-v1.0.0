# logging_setup.py
import logging
import os
from logging.handlers import RotatingFileHandler
import colorlog

def setup_logger(log_file: str = "data/logs/automation.log") -> logging.Logger:
    """
    Returns a configured logger with colored console output and rotating file logs.
    """
    logger = logging.getLogger("automator")
    logger.setLevel(logging.DEBUG)   # sab levels capture karega

    # --- 1. Console handler (colored) ---
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)   # console pe INFO aur upar dikhega

    # colorlog formatter with custom colors per level
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',
        }
    )
    console.setFormatter(console_formatter)
    logger.addHandler(console)

    # --- 2. File handler (rotating, plain text) ---
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,   # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

# Default logger instance – ise import karke kahi bhi use kar sakte ho
logger = setup_logger()