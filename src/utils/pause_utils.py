# src/utils/pause_utils.py
import os
import time
from src.config.config import PAUSE_FILE, STEP_FILE
from src.utils.logging_setup import logger

def check_pause_or_step():
    """Wait if pause.flag exists; wait for Enter if step.flag exists."""
    if os.path.exists(PAUSE_FILE):
        logger.info("⏸️  Paused – delete 'pause.flag' to resume.")
        while os.path.exists(PAUSE_FILE):
            time.sleep(2)
    if os.path.exists(STEP_FILE):
        try:
            input("🔹 Step mode – Press Enter to continue to next step...")
        except (EOFError, OSError):
            logger.info("🔹 Step mode requested but no console input, continuing automatically.")