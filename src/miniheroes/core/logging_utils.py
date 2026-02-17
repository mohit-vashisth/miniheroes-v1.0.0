import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def log_tap(device_id: str, x: int, y: int, wait_time: float):
    timestamp = datetime.now().strftime("%H:%M:%S")
    logger.info(f"[TAP] {device_id} - Tap at ({x}, {y}) - Wait {wait_time}s [{timestamp}]")

def log_action(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    logger.info(f"[ACTION] {message} [{timestamp}]")