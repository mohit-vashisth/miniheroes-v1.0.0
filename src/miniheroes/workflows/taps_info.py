from __future__ import annotations

import subprocess

from ..core.logger import log

logger = log()


def tap(device_id: str, x: int, y: int):
    """Perform a single tap at coordinates (x, y)"""
    logger.debug(f"[TAP] {device_id} - Simple tap at ({x}, {y})")

    try:
        subprocess.run(
            ["adb", "-s", device_id, "shell", "input", "tap", str(x), str(y)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        logger.debug(f"[TAP] Tap completed on {device_id}")
    except subprocess.TimeoutExpired:
        logger.warning(f"[TAP] Timeout while tapping on {device_id} at ({x}, {y})")
    except Exception as e:
        logger.error(f"[TAP] Error tapping on {device_id} at ({x}, {y}): {e}")


def adb_type(device_id: str, text: str):
    """Type text on device"""
    logger.debug(f"[TYPE] {device_id} - Typing text: '{text}'")

    # Replace spaces with %s for ADB shell
    safe_text = text.replace(" ", "%s")
    logger.debug(f"[TYPE] Safe text: '{safe_text}'")

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