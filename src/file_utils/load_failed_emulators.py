# src/file_utils/load_failed_emulators.py
import os
from typing import Set
from src.config.config import FAILED_EMULATORS_FILE

def load_failed_emulators() -> Set[int]:
    """Return set of failed emulator indices. Empty set if file doesn't exist."""
    if not os.path.exists(FAILED_EMULATORS_FILE):
        return set()
    with open(FAILED_EMULATORS_FILE, "r") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}