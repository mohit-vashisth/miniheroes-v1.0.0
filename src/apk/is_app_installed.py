# src/apk/is_app_installed.py
import subprocess
from src.config.config import LD_CONSOLE, GAME_PACKAGE
from src.utils.logging_setup import logger

def is_app_installed(index: int) -> bool:
    """Return True if the game package is installed on the emulator."""
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", f"shell pm list packages {GAME_PACKAGE}"],
            capture_output=True, text=True, timeout=10
        )
        return f"package:{GAME_PACKAGE}" in result.stdout
    except Exception as e:
        logger.error(f"[{index}] Install check error: {e}")
        return False