# src/file_utils/load_used_emulators.py
import os
from typing import Set
from src.config.config import USED_EMULATORS_FILE

def load_used_emulators() -> Set[int]:
    """Return set of used emulator indices. Empty set if file doesn't exist."""
    if not os.path.exists(USED_EMULATORS_FILE):
        return set()
    with open(USED_EMULATORS_FILE, "r") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}