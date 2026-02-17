# taps_player.py
from __future__ import annotations

import time
from typing import List

from .taps_info import adb_type, tap


def run_steps(device_id: str, steps: List[tuple], verbose: bool = True):
    for idx, step in enumerate(steps, start=1):
        action = step[0]

        if action == "wait":
            wait_seconds = float(step[1])
            if verbose:
                print(f"[{idx}] WAIT {wait_seconds}s")
            time.sleep(wait_seconds)
            continue

        if action == "tap":
            x = int(step[1])
            y = int(step[2])
            wait_seconds = float(step[3]) if len(step) > 3 else 0.0
            if verbose:
                print(f"[{idx}] TAP ({x}, {y}) wait={wait_seconds}s")
            tap(device_id, x, y)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            continue

        if action == "text":
            text_value = str(step[1])
            if verbose:
                print(f"[{idx}] TEXT '{text_value}'")
            adb_type(device_id, text_value)
            continue

        raise ValueError(f"Unknown step: {step}")

