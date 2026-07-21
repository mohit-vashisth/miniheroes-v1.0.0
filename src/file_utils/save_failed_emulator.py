# src/file_utils/save_failed_emulator.py
import os
from src.config.config import FAILED_EMULATORS_FILE
from src.utils.logging_setup import logger

def save_failed_emulator(index: int):
    """Append index to failed file (thread‑safe enough for single‑writer use)."""
    os.makedirs(os.path.dirname(FAILED_EMULATORS_FILE), exist_ok=True)
    with open(FAILED_EMULATORS_FILE, "a") as f:
        f.write(f"{index}\n")
    logger.info(f"[{index}] Marked as failed.")