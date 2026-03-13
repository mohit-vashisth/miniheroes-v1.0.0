from __future__ import annotations

import time
from typing import List

from ..auth.email_utils import fetch_code_with_retry
from ..auth.used_accounts_track import save_used_gmail
from ..config.config import GAME_PACKAGE, LD_CONSOLE, MODE
from ..core.adb_utils import adb_tap, clear_app_data
from ..core.logger import log
from .taps_info import adb_type
from .split_apk_installer import is_app_installed, launch_app_e
from .taps_modes import (
    MAIN_SEQUENCE,
    MAIN_SEQUENCE_MODE2,
    MODE1_STEPS,
    MODE2_STEPS,
)
from .taps_player import run_steps_with_adb

logger = log()

# Decide which main sequence to use based on MODE
if MODE == 1:
    MAIN_SEQ = MAIN_SEQUENCE
    STEPS_TEMPLATE = MODE1_STEPS
else:
    MAIN_SEQ = MAIN_SEQUENCE_MODE2
    STEPS_TEMPLATE = MODE2_STEPS


def _run_tap_sequence(device_id: str, taps: List[tuple]) -> bool:
    """Execute a sequence of taps using TAP → WAIT model"""
    total_taps = len(taps)

    logger.info(f"[TAP SEQ] Starting {total_taps} taps on {device_id}")

    for i, (x, y, wait_seconds) in enumerate(taps, 1):

        logger.info(
            f"[TAP] {device_id} - Tap {i}/{total_taps} at ({x},{y}) - Wait {wait_seconds}s"
        )

        ok = adb_tap(device_id, int(x), int(y), int(wait_seconds), LD_CONSOLE)

        if wait_seconds > 0:
            time.sleep(float(wait_seconds))

        if not ok:
            logger.warning(
                f"[TAP SEQ] Tap {i} failed on {device_id} at ({x},{y})"
            )
            return False

    return True


def tap_player(port: int, email: str, run_number: int) -> bool:

    device_id = f"emulator-{port}"

    logger.info(
        f"[RUN {run_number}/4] Starting on {device_id} with email: {email}"
    )

    try:

        # Launch game
        launch_app_e(device_id, GAME_PACKAGE)

        # Build pre-code steps
        pre_code_steps: List[tuple] = []

        for step in STEPS_TEMPLATE:

            if step[0] == "text" and len(step) > 1 and step[1] == "__CODE__":
                break

            if step[0] == "text" and len(step) > 1 and step[1] == "__EMAIL__":
                pre_code_steps.append(("text", email))
            else:
                pre_code_steps.append(step)

        run_steps_with_adb(device_id, pre_code_steps, LD_CONSOLE)

        # Fetch verification code
        logger.info(
            f"[RUN {run_number}] Waiting for verification code from {email}"
        )

        code = fetch_code_with_retry(email, max_wait=40, poll_interval=2.0)

        if not code:
            logger.error(
                f"[RUN {run_number}] Failed to get verification code for {email}"
            )
            return False

        logger.info(f"[RUN {run_number}] Got verification code: {code}")

        # Mark email as used
        save_used_gmail(email)

        # Enter code
        adb_type(device_id, code)

        time.sleep(2)

        # Execute main tap sequence
        logger.info(f"[RUN {run_number}] Executing main game sequence")

        _run_tap_sequence(device_id, MAIN_SEQ)

        logger.success(
            f"Run {run_number} completed successfully on {device_id}"
        )

        return True

    except Exception as exc:

        logger.error(f"[RUN {run_number}] Failed on {device_id}: {exc}")

        import traceback

        logger.debug(traceback.format_exc())

        return False


def process_single_emulator(emulator_index: int, email_list: List[str]) -> bool:

    port = 5554 + (emulator_index * 2)
    device_id = f"emulator-{port}"

    logger.section(f"Emulator {emulator_index}")

    if not is_app_installed(device_id, GAME_PACKAGE):
        logger.error(f"[EMU] Game not installed on {device_id}")
        return False

    if len(email_list) < 4:
        logger.error(
            f"[EMU] Expected 4 emails for emulator {emulator_index}"
        )
        return False

    successful_runs = 0

    for run_number in range(1, 5):

        clear_app_data(device_id, GAME_PACKAGE)

        time.sleep(2)

        if tap_player(port, email_list[run_number - 1], run_number):
            successful_runs += 1

        if run_number < 4:
            clear_app_data(device_id, GAME_PACKAGE)
            time.sleep(2)

    if successful_runs >= 3:
        logger.success(
            f"Emulator {emulator_index} completed: {successful_runs}/4 successful"
        )
    else:
        logger.fail(
            f"Emulator {emulator_index} completed: {successful_runs}/4 successful"
        )

    return successful_runs >= 3