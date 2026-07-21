# src/apk/install_and_verify_apks.py
import os
import time
import subprocess
from src.config.config import LD_CONSOLE, APK_DIR, APK_FILES, INSTALL_TIMEOUT
from src.utils.logging_setup import logger
from src.apk.is_app_installed import is_app_installed
from src.apk.clear_game_data import clear_game_data

def install_and_verify_apks(index: int, retries: int = 3) -> bool:
    """
    Install all APKs if game is not installed, then verify.
    If already installed, just clear data.
    Returns True on success.
    """
    if is_app_installed(index):
        logger.info(f"[{index}] Game already installed.")
        return clear_game_data(index)

    apk_paths = [os.path.join(APK_DIR, f) for f in APK_FILES]
    for path in apk_paths:
        if not os.path.isfile(path):
            logger.error(f"[{index}] APK missing: {path}")
            return False

    paths_quoted = [f'"{p}"' for p in apk_paths]
    install_cmd = f"install-multiple -r {' '.join(paths_quoted)}"

    for attempt in range(1, retries + 1):
        logger.info(f"[{index}] Install attempt {attempt}/{retries}...")
        try:
            res = subprocess.run(
                [LD_CONSOLE, "adb", "--index", str(index), "--command", install_cmd],
                capture_output=True, text=True, timeout=INSTALL_TIMEOUT
            )
        except subprocess.TimeoutExpired:
            logger.error(f"[{index}] Install timed out on attempt {attempt}")
            time.sleep(3)
            continue
        except Exception as e:
            logger.error(f"[{index}] Install error: {e}")
            time.sleep(3)
            continue

        if res.returncode != 0 and "Success" not in res.stdout:
            logger.error(f"[{index}] Install command failed: {res.stderr.strip()}")
            time.sleep(3)
            continue

        logger.info(f"[{index}] Verifying installation...")
        if is_app_installed(index):
            logger.info(f"[{index}] APKs installed successfully.")
            return clear_game_data(index)
        else:
            logger.error(f"[{index}] Package not found, will retry...")
            time.sleep(3)

    logger.error(f"[{index}] Installation failed after {retries} attempts.")
    return False