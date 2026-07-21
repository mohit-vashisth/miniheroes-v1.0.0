# src/file_utils/save_used_emulator.py
import os
from src.config.config import USED_EMULATORS_FILE
from src.utils.logging_setup import logger
from src.file_utils.tracking_state import used_emulators_lock

def save_used_emulator(index: int):
    """Thread‑safe, no duplicates. Append index to used file."""
    with used_emulators_lock:
        if not os.path.exists(USED_EMULATORS_FILE):
            open(USED_EMULATORS_FILE, 'w').close()
        existing = set()
        with open(USED_EMULATORS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line.isdigit():
                    existing.add(int(line))
        if index not in existing:
            with open(USED_EMULATORS_FILE, 'a') as f:
                f.write(f"{index}\n")
            logger.info(f"[{index}] Marked as used.")
        else:
            logger.error(f"[{index}] Already in used list, skipping.")