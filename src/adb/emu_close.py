# src/adb/emu_close.py
import subprocess
import time
from src.config.config import LD_CONSOLE
from src.utils.logging_setup import logger

def is_emulator_running(index: int) -> bool:
    try:
        res = subprocess.run(
            [LD_CONSOLE, "isrunning", "--index", str(index)],
            capture_output=True, text=True, timeout=5
        )
        return "running" in res.stdout.lower()
    except:
        return False

def force_close_emulator(index: int):
    logger.info(f"[{index}] Force-closing emulator...")
    try:
        subprocess.run([LD_CONSOLE, "quit", "--index", str(index)],
                       capture_output=True, timeout=10)
    except: pass
    try:
        subprocess.run([LD_CONSOLE, "quit", "--index", str(index), "--force"],
                       capture_output=True, timeout=10)
    except: pass
    for _ in range(10):
        if not is_emulator_running(index):
            logger.info(f"[{index}] Emulator successfully closed.")
            return
        time.sleep(1)
    logger.warning(f"[{index}] Emulator may still be running.")