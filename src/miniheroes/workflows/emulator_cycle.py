from __future__ import annotations

import time
from typing import List

from ..auth.email_utils import fetch_code_with_retry
from ..auth.used_accounts_track import save_used_gmail
from ..config.config import GAME_PACKAGE, LD_CONSOLE
from ..core.adb_utils import adb_tap, clear_app_data
from ..core.logger import log
from .split_apk_installer import is_app_installed, launch_app_e
from .taps_info import adb_type
from .taps_modes import MAIN_SEQUENCE, MODE1_STEPS
from .taps_player import run_steps


logger = log()


def _run_tap_sequence(device_id: str, taps: List[tuple]) -> bool:
    """Execute a sequence of taps"""
    total_taps = len(taps)
    logger.debug(f"[TAP SEQ] Starting {total_taps} taps on {device_id}")

    for i, (x, y, wait_seconds) in enumerate(taps, 1):
        logger.debug(f"[TAP SEQ] Tap {i}/{total_taps}: ({x}, {y}) wait={wait_seconds}s")
        ok = adb_tap(device_id, int(x), int(y), int(wait_seconds), LD_CONSOLE)
        time.sleep(float(wait_seconds))
        if not ok:
            logger.warning(f"[TAP SEQ] Tap {i} failed on {device_id} at ({x}, {y})")
            return False
    return True


def _run_steps_with_adb_fallback(device_id: str, steps: List[tuple]) -> bool:
    """Execute steps with fallback handling"""
    logger.debug(f"[STEPS] Running {len(steps)} steps on {device_id}")

    for i, step in enumerate(steps, 1):
        action = step[0]
        logger.debug(f"[STEPS] Step {i}/{len(steps)}: {step}")

        if action == "wait":
            time.sleep(float(step[1]))
            continue

        if action == "text":
            text = str(step[1])
            logger.debug(f"[STEPS] Typing text on {device_id}")
            adb_type(device_id, text)
            continue

        if action == "tap":
            x = int(step[1])
            y = int(step[2])
            wait_seconds = float(step[3]) if len(step) > 3 else 0.0
            logger.debug(f"[STEPS] Tapping ({x}, {y}) on {device_id}")
            adb_tap(device_id, x, y, int(wait_seconds), LD_CONSOLE)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            continue

        logger.warning(f"[STEPS] Unknown step ignored: {step}")

    return True


def tap_player(port: int, email: str, run_number: int) -> bool:
    """Run the complete tap sequence for one account on one emulator"""
    device_id = f"emulator-{port}"
    logger.info(f"[RUN {run_number}/4] Starting on {device_id} with email: {email}")

    try:
        # Launch game
        logger.debug(f"[RUN {run_number}] Launching game on {device_id}")
        launch_app_e(device_id, GAME_PACKAGE)

        # Process pre-code steps (everything before code entry)
        logger.debug(f"[RUN {run_number}] Processing pre-code steps")
        pre_code_steps: List[tuple] = []
        for step in MODE1_STEPS:
            if step[0] == "text" and len(step) > 1 and step[1] == "__CODE__":
                break
            if step[0] == "text" and len(step) > 1 and step[1] == "__EMAIL__":
                pre_code_steps.append(("text", email))
            else:
                pre_code_steps.append(step)

        _run_steps_with_adb_fallback(device_id, pre_code_steps)

        # Fetch verification code
        logger.info(f"[RUN {run_number}] Waiting for verification code from {email}")
        code = fetch_code_with_retry(email, max_wait=40, poll_interval=2.0)
        if not code:
            logger.error(f"[RUN {run_number}] Failed to get verification code for {email}")
            return False

        logger.info(f"[RUN {run_number}] Got verification code: {code}")

        # Enter code
        run_steps(device_id, [("text", code)], verbose=False)
        run_steps(device_id, [("wait", 2)], verbose=False)

        # Execute main sequence
        logger.info(f"[RUN {run_number}] Executing main game sequence")
        _run_tap_sequence(device_id, MAIN_SEQUENCE)

        # Save email as used
        save_used_gmail(email)
        logger.success(f"Run {run_number} completed successfully on {device_id}")
        return True

    except Exception as exc:
        logger.error(f"[RUN {run_number}] Failed on {device_id}: {exc}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


def process_single_emulator(emulator_index: int, email_list: List[str]) -> bool:
    """Process 4 account runs on a single emulator"""
    port = 5554 + (emulator_index * 2)
    device_id = f"emulator-{port}"

    logger.section(f"Emulator {emulator_index}")
    logger.info(f"Processing emulator {emulator_index} on {device_id} with {len(email_list)} emails")

    # Verify game is installed
    if not is_app_installed(device_id, GAME_PACKAGE):
        logger.error(f"[EMU] Game not installed on {device_id}")
        return False

    if len(email_list) < 4:
        logger.error(f"[EMU] Expected 4 emails for emulator {emulator_index}, got {len(email_list)}")
        return False

    # Run 4 cycles (accounts)
    successful_runs = 0
    for run_number in range(1, 5):
        logger.info(f"[EMU] Starting run {run_number}/4 on emulator {emulator_index}")

        # Clear app data before each run
        logger.debug(f"[EMU] Clearing app data for run {run_number}")
        clear_app_data(device_id, GAME_PACKAGE)
        time.sleep(2)

        # Execute the run
        if tap_player(port, email_list[run_number - 1], run_number):
            successful_runs += 1
            logger.info(f"[EMU] Run {run_number} successful ({successful_runs}/4 so far)")
        else:
            logger.warning(f"[EMU] Run {run_number} failed")

        # Clear for next cycle (except last)
        if run_number < 4:
            logger.debug(f"[EMU] Preparing for next run")
            clear_app_data(device_id, GAME_PACKAGE)
            time.sleep(2)

    # Final result
    result_text = f"Emulator {emulator_index} completed: {successful_runs}/4 successful"
    if successful_runs >= 3:
        logger.success(result_text)
    else:
        logger.fail(result_text)

    return successful_runs >= 3