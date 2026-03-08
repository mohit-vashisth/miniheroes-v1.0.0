from __future__ import annotations

import time
from typing import List

from ..auth.email_utils import fetch_code_with_retry
from ..auth.level35_track import save_level35_account
from ..config.config import GAME_PACKAGE, LD_CONSOLE
from ..core.logger import log
from .split_apk_installer import launch_app_e
from .taps_modes import MODE2_STEPS, LOGOUT_ACCOUNT
from .taps_player import run_steps_with_adb, run_steps

logger = log()


def process_one_account(device_id: str, email: str) -> bool:
    """
    Handle one account on a fixed emulator:
    - launch game
    - enter email, fetch code, enter code
    - run the full level‑up sequence (triple‑tapped)
    - logout
    - mark account as level‑35
    """
    logger.info(f"[ACCOUNT] Starting {email} on {device_id}")

    try:
        # 1. Launch game (assume we are at home screen; wait for it to load)
        logger.info(f"[{device_id}] Launching game...")
        launch_app_e(device_id, GAME_PACKAGE, wait=30)

        # 2. Build pre‑code steps (everything before the verification code)
        logger.info(f"[{device_id}] Preparing pre‑code steps...")
        pre_code_steps: List[tuple] = []
        for step in MODE2_STEPS:
            if step[0] == "text" and len(step) > 1 and step[1] == "__CODE__":
                break
            if step[0] == "text" and len(step) > 1 and step[1] == "__EMAIL__":
                # Insert a clear step before typing the new email
                pre_code_steps.append(("clear",))
                pre_code_steps.append(("text", email))
            else:
                pre_code_steps.append(step)

        # Execute pre‑code steps
        logger.info(f"[{device_id}] Executing pre‑code steps ({len(pre_code_steps)} steps)...")
        run_steps_with_adb(device_id, pre_code_steps, LD_CONSOLE)

        # 3. Fetch login verification code
        logger.info(f"[{device_id}] Fetching verification code for {email}...")
        code = fetch_code_with_retry(email, max_wait=40, poll_interval=2.0)
        if not code:
            logger.error(f"[{device_id}] Failed to get code for {email}")
            return False
        logger.info(f"[{device_id}] Got code {code} for {email}")

        # 4. Enter the code and wait a moment
        logger.info(f"[{device_id}] Entering code...")
        run_steps(device_id, [("text", code)], verbose=False)
        time.sleep(2)

        # 5. Find the part of MODE2_STEPS that comes after the code (the actual level‑up taps)
        code_index = None
        for i, step in enumerate(MODE2_STEPS):
            if step[0] == "text" and step[1] == "__CODE__":
                code_index = i
                break
        if code_index is None:
            logger.error("[ACCOUNT] Could not find __CODE__ step in MODE2_STEPS")
            return False

        main_steps = MODE2_STEPS[code_index + 1:]   # everything after the code
        logger.info(f"[{device_id}] Executing main level‑up sequence ({len(main_steps)} taps)...")
        run_steps_with_adb(device_id, main_steps, LD_CONSOLE)

        # 6. Logout
        logger.info(f"[{device_id}] Logging out {email}...")
        run_steps_with_adb(device_id, LOGOUT_ACCOUNT, LD_CONSOLE)

        # 7. Mark as level‑35
        save_level35_account(email)
        logger.success(f"Account {email} reached level 35 and logged out on {device_id}")
        return True

    except Exception as e:
        logger.error(f"[{device_id}] Failed for {email}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False