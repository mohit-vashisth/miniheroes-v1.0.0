# src/yaml_exec/executor.py
import time
import yaml
import random
from typing import Optional, List

from src.utils.logging_setup import logger
from src.utils import vision
from src.adb.tap import tap
from src.adb.type_text import type_text
from src.otp.otp_fetcher import fetch_verification_code
from src.utils.pause_utils import check_pause_or_step
from src.utils.step_jump import get_skip_until_step
from src.config.config import CODES as DEFAULT_CODES

def execute_yaml_script(
    index: int,
    yaml_path: str,
    email: str,
    *,
    codes: Optional[List[str]] = None,
    wait_retries: int = 30,
    wait_interval: float = 0.9,
    tap_retries: int = 2,
    tap_interval: float = 0.5,
    skip_until: Optional[int] = None,
    enable_pause: bool = False,
) -> bool:
    """
    Execute YAML automation steps on the given emulator index.
    - codes: redeem codes list (if needed).
    - wait_retries / wait_interval: defaults used for all 'wait' steps.
    - tap_retries / tap_interval: defaults used for 'tap' image checks.
    - skip_until: step number to jump to (ignores earlier steps).
    - enable_pause: if True, checks pause.flag / step.flag between steps.
    Returns True if all steps completed successfully, False on failure.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data.get("steps", [])
    if not steps:
        logger.error("YAML file has no steps.")
        return False

    context = {"email": email, "otp": None}
    code_index = 0

    # Use provided skip_until or read from file
    if skip_until is None:
        skip_until = get_skip_until_step()

    for step_num, step in enumerate(steps, 1):
        # Jump
        if skip_until is not None and step_num < skip_until:
            continue

        if enable_pause:
            check_pause_or_step()

        step_type = list(step.keys())[0]
        params = step[step_type]
        logger.info(f"[{index}] Step {step_num}/{len(steps)}: {step_type}")

        if step_type == "wait":
            image = params["image"]
            confidence = params.get("confidence", 0.7)
            try:
                vision.wait_for_image(index, image, retries=wait_retries, interval=wait_interval, confidence=confidence)
            except TimeoutError:
                logger.error(f"[{index}] Image '{image}' not found – continuing.")

        elif step_type == "tap":
            image = params.get("image")
            x = params.get("x")
            y = params.get("y")
            confidence = params.get("confidence", 0.7)
            if image:
                try:
                    vision.wait_for_image(index, image, retries=tap_retries, interval=tap_interval, confidence=confidence)
                    logger.info(f"[{index}] Image '{image}' found – tapping coordinates.")
                except TimeoutError:
                    logger.warning(f"[{index}] Image '{image}' not found – tapping coordinates anyway.")
            if x is not None and y is not None:
                tap(index, x, y)
            else:
                logger.error(f"[{index}] Tap step missing x,y coordinates.")
                return False

        elif step_type == "sleep":
            seconds = params.get("seconds", 1)
            if seconds is None:
                seconds = 1
            logger.info(f"[{index}] Sleeping {seconds}s")
            time.sleep(seconds)

        elif step_type == "type_email":
            type_text(index, context["email"])

        elif step_type == "fetch_otp":
            if not context["email"]:
                logger.error(f"[{index}] No email in context.")
                return False
            time.sleep(random.uniform(0, 3))
            logger.info(f"[{index}] Fetching OTP...")
            code = fetch_verification_code(context["email"])
            if not code:
                logger.error(f"[{index}] OTP fetch failed.")
                return False
            context["otp"] = code

        elif step_type == "type_otp":
            if not context["otp"]:
                logger.error(f"[{index}] No OTP in context.")
                return False
            type_text(index, context["otp"])

        elif step_type == "type_text":
            if codes is None:
                codes = DEFAULT_CODES
            if not codes:
                logger.error(f"[{index}] No redeem codes available.")
                return False
            current_code = codes[code_index % len(codes)]
            code_index += 1
            logger.info(f"[{index}] Typing redeem code (fast): {current_code}")
            type_text(index, current_code, clear=False)

        else:
            logger.error(f"[{index}] Unknown step type '{step_type}' – skipping.")

    logger.info(f"[{index}] YAML script completed successfully.")
    return True