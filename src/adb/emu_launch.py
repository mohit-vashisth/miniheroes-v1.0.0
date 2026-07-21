# src/adb/emu_launch.py
import subprocess
from src.config.config import LD_CONSOLE
from src.utils.logging_setup import logger

def launch_emulator_by_index(index: int) -> bool:
    cmd = [LD_CONSOLE, "launch", "--index", str(index)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info(f"Emulator {index} launched successfully.")
            return True
        else:
            logger.error(f"Failed to launch emulator {index}: {result.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False