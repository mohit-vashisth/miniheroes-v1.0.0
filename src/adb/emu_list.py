# src/adb/emu_list.py
import subprocess
from typing import List
from src.config.config import LD_CONSOLE
from src.utils.logging_setup import logger

def get_all_emulator_indices() -> List[int]:
    try:
        result = subprocess.run([LD_CONSOLE, "list2"], capture_output=True, text=True, timeout=10)
        indices = []
        for line in result.stdout.splitlines():
            parts = [p.strip() for p in line.split(',')]
            if parts and parts[0].isdigit():
                indices.append(int(parts[0]))
        return sorted(set(indices))
    except Exception as e:
        logger.error(f"Error reading emulator list: {e}")
        return []