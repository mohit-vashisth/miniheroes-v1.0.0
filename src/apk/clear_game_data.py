# src/apk/clear_game_data.py
import subprocess
from src.config.config import LD_CONSOLE, GAME_PACKAGE
from src.utils.logging_setup import logger

def clear_game_data(index: int) -> bool:
    """Clear the game's app data. Returns True on success."""
    logger.info(f"[{index}] Clearing game data...")
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", f"shell pm clear {GAME_PACKAGE}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 or "Success" in result.stdout:
            logger.info(f"[{index}] Game data cleared.")
            return True
        else:
            logger.error(f"[{index}] Clear data failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"[{index}] Clear data error: {e}")
        return False