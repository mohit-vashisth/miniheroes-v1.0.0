# src/adb/type_text.py
import subprocess
import time
from src.config.config import LD_CONSOLE
from src.utils.logging_setup import logger

def type_text(index: int, text: str, clear: bool = True) -> bool:
    if clear:
        for _ in range(40):
            try:
                subprocess.run(
                    [LD_CONSOLE, "adb", "--index", str(index), "--command", "shell input keyevent 67"],
                    capture_output=True, text=True, timeout=2
                )
            except: pass
        for _ in range(40):
            try:
                subprocess.run(
                    [LD_CONSOLE, "adb", "--index", str(index), "--command", "shell input keyevent 112"],
                    capture_output=True, text=True, timeout=2
                )
            except: pass
        time.sleep(0.1)
    safe_text = text.replace(" ", "%s")
    try:
        res = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", f"shell input text {safe_text}"],
            capture_output=True, text=True, timeout=10
        )
        if res.returncode == 0:
            logger.info(f"[{index}] Text typed: {text}")
            return True
        else:
            logger.error(f"[{index}] Type failed: {res.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"[{index}] Type error: {e}")
        return False