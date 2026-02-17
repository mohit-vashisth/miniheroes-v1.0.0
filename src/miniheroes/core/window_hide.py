# window_hide.py
from __future__ import annotations

import logging
import subprocess
import time

import pyautogui
import win32con
import win32gui


logger = logging.getLogger(__name__)


def find_emulator_window(index: int):
    patterns = [
        f"LDPlayer{index}",
        f"LDPlayer-{index}",
        f"\u96f7\u7535\u6a21\u62df\u5668{index}",
        f"LDPlayer{index} -",
        f"LDPlayer {index}",
    ]

    for title in patterns:
        hwnd = win32gui.FindWindow(None, title)
        if hwnd:
            return hwnd

    matches = []

    def _enum_callback(hwnd, _):
        window_title = win32gui.GetWindowText(hwnd)
        if any(token in window_title for token in patterns):
            matches.append(hwnd)
        return True

    win32gui.EnumWindows(_enum_callback, None)
    return matches[0] if matches else None


def hide_emulator_window(index: int, console_path: str) -> bool:
    logger.info("[HIDE] attempting for emulator %s", index)

    try:
        result = subprocess.run(
            [
                console_path,
                "modify",
                "--index",
                str(index),
                "--window",
                "-9999,-9999,400,800",
            ],
            check=False,
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            logger.info("[HIDE] emulator %s moved off-screen", index)
            return True
    except Exception as exc:
        logger.debug("[HIDE] method1 failed for %s: %s", index, exc)

    try:
        hwnd = find_emulator_window(index)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            logger.info("[HIDE] emulator %s minimized with win32", index)
            return True
    except Exception as exc:
        logger.debug("[HIDE] method2 failed for %s: %s", index, exc)

    try:
        hwnd = find_emulator_window(index)
        if hwnd:
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.2)
            pyautogui.hotkey("alt", "space")
            time.sleep(0.1)
            pyautogui.press("n")
            logger.info("[HIDE] emulator %s minimized with keyboard", index)
            return True
    except Exception as exc:
        logger.debug("[HIDE] method3 failed for %s: %s", index, exc)

    try:
        port = 5554 + (index * 2)
        device = f"emulator-{port}"
        result = subprocess.run(
            ["adb", "-s", device, "shell", "input", "keyevent", "3"],
            check=False,
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            logger.info("[HIDE] emulator %s backgrounded with HOME key", index)
            return True
    except Exception as exc:
        logger.debug("[HIDE] method4 failed for %s: %s", index, exc)

    logger.warning("[HIDE] failed to hide emulator %s", index)
    return False
