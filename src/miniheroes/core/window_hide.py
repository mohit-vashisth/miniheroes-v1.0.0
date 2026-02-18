from __future__ import annotations

import subprocess
import time

import pyautogui
import win32con
import win32gui

from ..core.logger import log

logger = log()


def find_emulator_window(index: int):
    """Find window handle of LDPlayer emulator by index (multiple patterns)"""
    patterns = [
        f"LDPlayer{index}",
        f"LDPlayer-{index}",
        f"\u96f7\u7535\u6a21\u62df\u5668{index}",  # 雷电模拟器{index}
        f"LDPlayer{index} -",
        f"LDPlayer {index}",
    ]

    logger.debug(f"[WINDOW] Searching for emulator {index} with patterns: {patterns}")

    for title in patterns:
        hwnd = win32gui.FindWindow(None, title)
        if hwnd:
            window_title = win32gui.GetWindowText(hwnd)
            logger.debug(f"[WINDOW] Found window with title: '{window_title}'")
            return hwnd

    # EnumWindows fallback
    matches = []

    def _enum_callback(hwnd, _):
        window_title = win32gui.GetWindowText(hwnd)
        if any(token in window_title for token in patterns):
            logger.debug(f"[WINDOW] Fallback found: '{window_title}'")
            matches.append(hwnd)
        return True

    win32gui.EnumWindows(_enum_callback, None)

    if matches:
        logger.debug(f"[WINDOW] Found {len(matches)} matching windows, using first")
        return matches[0]

    logger.debug(f"[WINDOW] No window found for emulator {index}")
    return None


def hide_emulator_window(index: int, console_path: str) -> bool:
    """Hide emulator window using multiple fallback methods"""
    logger.info(f"[HIDE] Attempting to hide emulator {index}")

    # ----- METHOD 1: Off-screen positioning (dnconsole modify) -----
    try:
        cmd = [
            console_path,
            "modify",
            "--index",
            str(index),
            "--window",
            "-9999,-9999,400,800",
        ]
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            # Verify if window moved off-screen
            hwnd = find_emulator_window(index)
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                if rect[0] < -9000:  # Successfully moved off-screen
                    logger.success(f"Emulator {index} moved off-screen")
                    return True
                else:
                    logger.debug(f"[HIDE] Window rect: {rect}")
            logger.info(f"[HIDE] emulator {index} modify command succeeded")
            return True
    except Exception as exc:
        logger.debug(f"[HIDE] Method 1 failed for {index}: {exc}")

    # ----- METHOD 2: Minimize using Windows API -----
    try:
        hwnd = find_emulator_window(index)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            logger.success(f"Emulator {index} minimized with Windows API")
            return True
    except Exception as exc:
        logger.debug(f"[HIDE] Method 2 failed for {index}: {exc}")

    # ----- METHOD 3: Keyboard shortcut (Alt+Space, N) -----
    try:
        hwnd = find_emulator_window(index)
        if hwnd:
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.2)
            pyautogui.hotkey("alt", "space")
            time.sleep(0.1)
            pyautogui.press("n")
            logger.success(f"Emulator {index} minimized via keyboard")
            return True
    except Exception as exc:
        logger.debug(f"[HIDE] Method 3 failed for {index}: {exc}")

    # ----- METHOD 4: Send Home button (adb) to background -----
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
            logger.success(f"Emulator {index} sent to background (Home key)")
            return True
    except Exception as exc:
        logger.debug(f"[HIDE] Method 4 failed for {index}: {exc}")

    logger.warning(f"[HIDE] Failed to hide emulator {index} - all methods failed")
    return False