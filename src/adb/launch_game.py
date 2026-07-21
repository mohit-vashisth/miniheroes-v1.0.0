# src/adb/launch_game.py
import subprocess
from src.config.config import LD_CONSOLE, GAME_PACKAGE
from src.utils.logging_setup import logger

def launch_game(index: int) -> bool:
    cmd = f"shell monkey -p {GAME_PACKAGE} -c android.intent.category.LAUNCHER 1"
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", cmd],
            capture_output=True, text=True, timeout=15
        )
        if "Events injected" in result.stdout:
            logger.info(f"[{index}] Game launched.")
            return True
        else:
            logger.error(f"[{index}] Launch failed: {result.stdout.strip()}")
            return False
    except Exception as e:
        logger.error(f"[{index}] Launch error: {e}")
        return False