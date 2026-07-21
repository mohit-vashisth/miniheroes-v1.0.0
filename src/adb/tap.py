# src/adb/tap.py
import subprocess
from src.config.config import LD_CONSOLE
from src.utils.logging_setup import logger

def tap(index: int, x: int, y: int) -> bool:
    cmd = f"shell input tap {x} {y}"
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", cmd],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            logger.info(f"[{index}] Tapped ({x},{y})")
            return True
        else:
            logger.error(f"[{index}] Tap failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"[{index}] Tap error: {e}")
        return False