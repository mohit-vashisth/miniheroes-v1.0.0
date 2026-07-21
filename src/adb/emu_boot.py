# src/adb/emu_boot.py
import subprocess
import time
from src.config.config import LD_CONSOLE, BOOT_TIMEOUT
from src.utils.logging_setup import logger

def is_boot_completed(index: int) -> bool:
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", "shell getprop sys.boot_completed"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() == "1"
    except Exception as e:
        logger.error(f"Boot check error: {e}")
        return False

def wait_for_boot(index: int, timeout: int = BOOT_TIMEOUT) -> bool:
    logger.info(f"[{index}] Waiting for boot... (timeout = {timeout}s)")
    start = time.time()
    attempt = 0
    while time.time() - start < timeout:
        attempt += 1
        elapsed = int(time.time() - start)
        logger.info(f"[{index}] Boot check {attempt}... ({elapsed}s elapsed)")
        try:
            if is_boot_completed(index):
                logger.info(f"[{index}] Boot completed after {elapsed}s")
                return True
        except Exception as e:
            logger.error(f"[{index}] Boot error: {e}")
        time.sleep(2)
    logger.error(f"[{index}] Boot timeout!")
    return False