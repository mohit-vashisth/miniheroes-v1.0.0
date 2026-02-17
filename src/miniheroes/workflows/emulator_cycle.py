# emulator_cycle.py
from __future__ import annotations

import logging
import time
from typing import List

from ..auth.email_utils import fetch_code_with_retry
from ..auth.used_accounts_track import save_used_gmail
from ..config.config import GAME_PACKAGE, LD_CONSOLE
from ..core.adb_utils import adb_tap, clear_app_data
from .split_apk_installer import is_app_installed, launch_app_e
from .taps_info import adb_type
from .taps_modes import MAIN_SEQUENCE, MODE1_STEPS
from .taps_player import run_steps


logger = logging.getLogger(__name__)


def _run_tap_sequence(device_id: str, taps: List[tuple]) -> bool:
    for x, y, wait_seconds in taps:
        ok = adb_tap(device_id, int(x), int(y), int(wait_seconds), LD_CONSOLE)
        time.sleep(float(wait_seconds))
        if not ok:
            logger.warning("[TAP] failed on %s at (%s,%s)", device_id, x, y)
    return True


def _run_steps_with_adb_fallback(device_id: str, steps: List[tuple]) -> bool:
    for step in steps:
        action = step[0]
        if action == "wait":
            time.sleep(float(step[1]))
            continue
        if action == "text":
            adb_type(device_id, str(step[1]))
            continue
        if action == "tap":
            x = int(step[1])
            y = int(step[2])
            wait_seconds = float(step[3]) if len(step) > 3 else 0.0
            adb_tap(device_id, x, y, int(wait_seconds), LD_CONSOLE)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            continue
        logger.warning("[RUN] unknown step ignored: %s", step)
    return True


def tap_player(port: int, email: str, run_number: int) -> bool:
    device_id = f"emulator-{port}"
    logger.info("[RUN %s] %s using %s", run_number, device_id, email)

    try:
        launch_app_e(device_id, GAME_PACKAGE, wait=2.0)

        pre_code_steps: List[tuple] = []
        for step in MODE1_STEPS:
            if step[0] == "text" and len(step) > 1 and step[1] == "__CODE__":
                break
            if step[0] == "text" and len(step) > 1 and step[1] == "__EMAIL__":
                pre_code_steps.append(("text", email))
            else:
                pre_code_steps.append(step)
        _run_steps_with_adb_fallback(device_id, pre_code_steps)

        code = fetch_code_with_retry(email, max_wait=40, poll_interval=2.0)
        if not code:
            logger.error("[CODE] not found for %s", email)
            return False

        run_steps(device_id, [("text", code)], verbose=False)
        run_steps(device_id, [("wait", 2)], verbose=False)

        _run_tap_sequence(device_id, MAIN_SEQUENCE)

        save_used_gmail(email)
        logger.info("[RUN %s] success on %s", run_number, device_id)
        return True
    except Exception as exc:
        logger.error("[RUN %s] failed on %s: %s", run_number, device_id, exc)
        return False


def process_single_emulator(emulator_index: int, email_list: List[str]) -> bool:
    device_id = f"emulator-{5554 + (emulator_index * 2)}"
    logger.info("[EMU] processing index=%s device=%s", emulator_index, device_id)

    if not is_app_installed(device_id, GAME_PACKAGE):
        logger.error("[EMU] game not installed on %s", device_id)
        return False

    if len(email_list) < 4:
        logger.error("[EMU] expected 4 emails for emulator %s, got %s", emulator_index, len(email_list))
        return False

    successful_runs = 0
    for run_number in range(1, 5):
        clear_app_data(device_id, GAME_PACKAGE)
        time.sleep(2)

        if tap_player(5554 + (emulator_index * 2), email_list[run_number - 1], run_number):
            successful_runs += 1

        if run_number < 4:
            clear_app_data(device_id, GAME_PACKAGE)
            time.sleep(2)

    logger.info("[EMU] index=%s result=%s/4", emulator_index, successful_runs)
    return successful_runs >= 3
