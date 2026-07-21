import os
import time
import yaml
from typing import Optional

import vision          # tumhara vision.py (wait_for_image, tap_on_image)
# maan lo ye functions main.py ya kisi module mein hain, unhe import karo:
from register import tap, type_text, fetch_verification_code

# Agar email generator alag hai to use bhi import karo (optional)
# from main import get_next_email

def execute_yaml_script(
    index: int,
    yaml_path: str,
    email: Optional[str] = None,
    otp: Optional[str] = None
) -> bool:
    """
    YAML script ko step-by-step execute karta hai.
    index       – emulator index
    yaml_path   – YAML file ka path (e.g., "templates/scripts/register.yaml")
    email       – agar provide kiya to use karega, nahi to None (type_email step ke liye)
    otp         – agar pehle se fetched ho to use karega
    Returns True if script successfully completed, else False.
    """
    # YAML load karo
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data.get("steps", [])
    if not steps:
        print("YAML file has no steps.")
        return False

    context = {
        "email": email,
        "otp": otp
    }

    for step_num, step in enumerate(steps, 1):
        step_type = list(step.keys())[0]
        params = step[step_type]
        print(f"[Step {step_num}/{len(steps)}] {step_type}: {params}")

        # --- WAIT ---
        if step_type == "wait":
            image = params["image"]
            retries = params.get("retries", 10)
            confidence = params.get("confidence", 0.8)
            try:
                vision.wait_for_image(index, image, retries=retries, interval=1.0, confidence=confidence)
            except TimeoutError:
                print(f"  [WARN] Image '{image}' not found – continuing.")
                # Wait fail hone par bhi aage badho (tap fallback sambhal lega)

        # --- TAP ---
        elif step_type == "tap":
            image = params["image"]
            x_fallback = params.get("x")
            y_fallback = params.get("y")
            retries = params.get("retries", 2)
            confidence = params.get("confidence", 0.8)
            try:
                vision.tap_on_image(index, image, retries=retries, interval=1.5, confidence=confidence)
            except TimeoutError:
                if x_fallback is not None and y_fallback is not None:
                    print(f"  [FALLBACK] Tapping coordinates ({x_fallback},{y_fallback})")
                    tap(index, x_fallback, y_fallback)
                else:
                    print("  [ERROR] Tap failed and no fallback coordinates.")
                    return False

        # --- SLEEP ---
        elif step_type == "sleep":
            seconds = params.get("seconds", 1)
            if seconds is None:   # safety for empty value
                seconds = 1
            print(f"  Sleeping {seconds}s")
            time.sleep(seconds)

        # --- TYPE_EMAIL ---
        elif step_type == "type_email":
            if not context["email"]:
                print("  [ERROR] No email in context.")
                return False
            type_text(index, context["email"])

        # --- FETCH_OTP ---
        elif step_type == "fetch_otp":
            if not context["email"]:
                print("  [ERROR] No email to fetch OTP.")
                return False
            print("  Fetching OTP...")
            code = fetch_verification_code(context["email"])
            if not code:
                print("  [ERROR] OTP fetch failed.")
                return False
            context["otp"] = code
            print(f"  OTP received: {code}")

        # --- TYPE_OTP ---
        elif step_type == "type_otp":
            if not context["otp"]:
                print("  [ERROR] No OTP in context.")
                return False
            type_text(index, context["otp"])

        else:
            print(f"  [WARN] Unknown step type '{step_type}' – skipping.")

    print("YAML script completed successfully.")
    return True