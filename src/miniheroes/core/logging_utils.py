from datetime import datetime

from ..core.logger import log

logger = log()


def log_tap(device_id: str, x: int, y: int, wait_time: float):
    """Log tap actions with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    logger.info(f"[TAP] {device_id} - Tap at ({x}, {y}) - Wait {wait_time}s [{timestamp}]")


def log_action(message: str):
    """Log general actions with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    logger.info(f"[ACTION] {message} [{timestamp}]")