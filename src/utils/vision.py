# vision.py
import time
import cv2
import numpy as np
import subprocess
import os
import threading
from typing import Tuple

from src.config.config import ADB_PATH, CROPS_DIR

_screencap_lock = threading.Lock()

def _get_serial(index: int) -> str:
    port = 5554 + index * 2
    return f"emulator-{port}"

def _screencap(index: int) -> np.ndarray:
    """Capture screenshot via exec-out, keep in color (BGR)."""
    with _screencap_lock:
        serial = _get_serial(index)
        result = subprocess.run(
            [ADB_PATH, "-s", serial, "exec-out", "screencap", "-p"],
            capture_output=True, timeout=15
        )
        if result.returncode != 0 or not result.stdout:
            raise RuntimeError("Screenshot failed")
        img_array = np.frombuffer(result.stdout, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("Could not decode screenshot")
        return img   # BGR color

def load_template(template_name: str) -> np.ndarray:
    """Load template from templates/crops/ as color (BGR)."""
    path = os.path.join(CROPS_DIR, template_name)
    img = cv2.imread(path, cv2.IMREAD_COLOR)   # color
    if img is None:
        raise FileNotFoundError(f"Template not found: {path}")
    return img

def wait_for_image(index: int, template_name: str, retries: int = 3,
                   interval: float = 1.5, confidence: float = 0.7) -> Tuple[int, int]:
    """Try to find the template on screen up to `retries` times.
    Returns center (x, y) of the matched template.
    Raises TimeoutError if not found after all retries.
    Now also catches missing template files and converts to TimeoutError.
    """
    # --- Safe template loading ---
    try:
        template = load_template(template_name)
    except FileNotFoundError as e:
        print(f"[VISION] ERROR: {e} – continuing without image.")
        raise TimeoutError(str(e))

    h, w = template.shape[:2]

    for attempt in range(1, retries + 1):
        try:
            screen = _screencap(index)   # color
        except Exception as e:
            print(f"[VISION] Attempt {attempt}/{retries}: screenshot failed ({e}), retrying...")
            if attempt < retries:
                time.sleep(interval)
            continue

        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            print(f"[VISION] Found '{template_name}' at ({center_x},{center_y}) confidence {max_val:.2f} (attempt {attempt})")
            return center_x, center_y

        print(f"[VISION] Attempt {attempt}/{retries}: '{template_name}' not found (confidence {max_val:.2f})")
        if attempt < retries:
            time.sleep(interval)

    raise TimeoutError(f"Template '{template_name}' not found after {retries} retries")

def tap_on_image(index: int, template_name: str, retries: int = 3,
                 interval: float = 1.5, confidence: float = 0.8) -> None:
    """(Unused if you switch to coordinate-tap) – kept for backward compatibility."""
    x, y = wait_for_image(index, template_name, retries, interval, confidence)
    subprocess.run(
        ["D:\\LDPlayer\\LDPlayer9\\ldconsole.exe", "adb", "--index", str(index),
         "--command", f"shell input tap {x} {y}"],
        capture_output=True, text=True, timeout=5
    )