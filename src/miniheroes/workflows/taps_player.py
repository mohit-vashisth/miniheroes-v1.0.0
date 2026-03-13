from __future__ import annotations

import time
from typing import List

from ..core.logger import log
from .taps_info import adb_type, tap

logger = log()


def run_steps(device_id: str, steps: List[tuple], verbose: bool = True):
    for idx, step in enumerate(steps, start=1):
        action = step[0]

        if action == "wait":
            wait_seconds = float(step[1])
            if verbose:
                logger.info(f"[{idx}] WAIT {wait_seconds}s")
            time.sleep(wait_seconds)
            continue

        if action == "tap":
            x = int(step[1])
            y = int(step[2])
            wait_seconds = float(step[3]) if len(step) > 3 else 0.0
            if verbose:
                logger.info(f"[{idx}] TAP ({x}, {y}) wait={wait_seconds}s")
            tap(device_id, x, y)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            continue

        if action == "text":
            text_value = str(step[1])
            if verbose:
                logger.info(f"[{idx}] TEXT '{text_value}'")
            adb_type(device_id, text_value)
            continue

        raise ValueError(f"Unknown step: {step}")


def run_steps_with_adb(device_id: str, steps: List[tuple], console_path: str) -> None:
    from ..core.adb_utils import adb_tap  # local import to avoid circular dependency
    import subprocess

    for idx, step in enumerate(steps, start=1):
        action = step[0]
        if action == "wait":
            wait_seconds = float(step[1])
            logger.info(f"[STEP {idx}] WAIT {wait_seconds}s on {device_id}")
            time.sleep(wait_seconds)
        elif action == "text":
            text = str(step[1])
            logger.info(f"[STEP {idx}] TEXT '{text}' on {device_id}")
            adb_type(device_id, text)
        elif action == "tap":
            x = int(step[1])
            y = int(step[2])
            wait_seconds = float(step[3]) if len(step) > 3 else 0.0
            # Only log if wait is significant (more than 0.02s) – i.e., the main tap
            if wait_seconds > 0.02:
                logger.info(f"[STEP {idx}] TAP ({x}, {y}) wait={wait_seconds}s on {device_id}")
            else:
                logger.debug(f"[STEP {idx}] Quick TAP ({x}, {y}) on {device_id}")
            adb_tap(device_id, x, y, wait_seconds, console_path)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
        elif action == "clear":
            logger.info(f"[STEP {idx}] CLEAR text field on {device_id} (move to end + backspace)")
            # Move cursor to end of field
            subprocess.run(
                ["adb", "-s", device_id, "shell", "input", "keyevent", "123"],  # KEYCODE_MOVE_END
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            time.sleep(0.1)
            # Send many backspaces (e.g., 100) to delete any text
            for _ in range(100):
                subprocess.run(
                    ["adb", "-s", device_id, "shell", "input", "keyevent", "67"],  # KEYCODE_DEL
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                time.sleep(0.01)
        else:
            logger.warning(f"[STEP {idx}] Unknown step: {step}")