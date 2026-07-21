# src/utils/step_jump.py
import os
from typing import Optional
from src.config.config import WHERE_TO_STEP_FILE
from src.utils.logging_setup import logger

def get_skip_until_step() -> Optional[int]:
    """Read where_to_step.txt and return the step number to start from, or None."""
    if not os.path.exists(WHERE_TO_STEP_FILE):
        return None
    try:
        with open(WHERE_TO_STEP_FILE, "r") as f:
            num = int(f.read().strip())
        if num >= 1:
            logger.info(f"⏭️  Skipping steps until step {num} (read from {WHERE_TO_STEP_FILE})")
            return num
    except Exception:
        pass
    return None