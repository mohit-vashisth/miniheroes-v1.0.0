# taps_info.py
from __future__ import annotations

import subprocess


def tap(device_id: str, x: int, y: int):
    subprocess.run(
        ["adb", "-s", device_id, "shell", "input", "tap", str(x), str(y)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def adb_type(device_id: str, text: str):
    safe_text = text.replace(" ", "%s")
    subprocess.run(
        ["adb", "-s", device_id, "shell", "input", "text", safe_text],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

