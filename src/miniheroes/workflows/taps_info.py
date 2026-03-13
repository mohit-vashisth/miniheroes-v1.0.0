from __future__ import annotations

import subprocess

from ..core.logger import log

logger = log()


def tap(device_id: str, x: int, y: int) -> bool:
    """Perform a single tap at coordinates (x, y)"""

    logger.debug(f"[TAP] {device_id} - Simple tap at ({x}, {y})")

    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "input", "tap", str(x), str(y)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )

        if result.returncode == 0:
            logger.debug(f"[TAP] Tap completed on {device_id}")
            return True
        else:
            logger.warning(f"[TAP] Tap command failed on {device_id}")
            return False

    except subprocess.TimeoutExpired:
        logger.warning(f"[TAP] Timeout while tapping on {device_id} at ({x}, {y})")
        return False

    except Exception as e:
        logger.error(f"[TAP] Error tapping on {device_id} at ({x}, {y}): {e}")
        return False


def adb_type(device_id: str, text: str):
    """Type text on device"""

    logger.debug(f"[TYPE] {device_id} - Typing text: '{text}'")

    # Replace spaces with %s for ADB shell
    safe_text = text.replace(" ", "%s")

    try:
        subprocess.run(
            ["adb", "-s", device_id, "shell", "input", "text", safe_text],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )

        logger.debug(f"[TYPE] Text typed successfully on {device_id}")

    except subprocess.TimeoutExpired:
        logger.warning(f"[TYPE] Timeout while typing on {device_id}")

    except Exception as e:
        logger.error(f"[TYPE] Error typing on {device_id}: {e}")