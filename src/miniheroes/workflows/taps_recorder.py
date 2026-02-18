# taps_recorder.py
from pathlib import Path

OUTPUT_FILE = r"E:\Github\miniheroes-v1.0.0\src\miniheroes\data\tap_steps.txt"

# ---------------- DPI AWARE (MUST BE FIRST) ----------------
try:
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# ---------------- IMPORTS ----------------
import sys
import time
import math
import threading
import queue
from pynput.mouse import Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener, Key
import pygetwindow as gw

try:
    import win32gui  # type: ignore
    WIN32_OK = True
except Exception:
    WIN32_OK = False

# ---------------- CONFIG ----------------
ANDROID_W = 720
ANDROID_H = 1280
ANDROID_DPI = 320  # informational, not used in math

LDPLAYER_KEYWORDS = ["ldplayer"]
DEBUG = "--debug" in sys.argv

# ---------------- STATE ----------------
tap_queue = queue.Queue()
ctrl_pressed = False
last_tap_time = None
time_lock = threading.Lock()

# ---------------- HELPERS ----------------
def debug_print(*args):
    if DEBUG:
        print("[DEBUG]", *args)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def append_to_file(line: str):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def window_matches_ldplayer(title: str):
    return any(k in (title or "").lower() for k in LDPLAYER_KEYWORDS)

def get_client_rect(hwnd):
    """
    Returns client-area rect in SCREEN coordinates
    (excludes borders + titlebar, DPI-safe)
    """
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    tl = win32gui.ClientToScreen(hwnd, (left, top))
    br = win32gui.ClientToScreen(hwnd, (right, bottom))
    return tl[0], tl[1], br[0], br[1]

def get_foreground_window_info():
    try:
        if WIN32_OK:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd)
            is_min = win32gui.IsIconic(hwnd)
            left, top, right, bottom = get_client_rect(hwnd)

            return hwnd, title, left, top, right, bottom, is_min
        else:
            win = gw.getActiveWindow()
            if not win:
                return None

            return (
                None,
                win.title,
                win.left,
                win.top,
                win.left + win.width,
                win.top + win.height,
                win.isMinimized,
            )
    except Exception:
        return None

# ---------------- FILE WRITER THREAD ----------------
def input_worker():
    while True:
        x, y, wait_time = tap_queue.get()
        line = f"tap(device_id, {x}, {y}, {wait_time})"
        append_to_file(line)
        print(f"[SAVED] {line}")
        tap_queue.task_done()

# ---------------- KEYBOARD ----------------
def on_key_press(key):
    global ctrl_pressed
    if key in (Key.ctrl_l, Key.ctrl_r):
        ctrl_pressed = True

def on_key_release(key):
    global ctrl_pressed
    if key in (Key.ctrl_l, Key.ctrl_r):
        ctrl_pressed = False

# ---------------- MOUSE HANDLER ----------------
def on_click(x, y, button, pressed):
    global last_tap_time

    if not pressed or ctrl_pressed:
        return

    info = get_foreground_window_info()
    if not info:
        return

    hwnd, title, left, top, right, bottom, is_min = info

    # Ignore minimized / non-LDPlayer
    if is_min or not window_matches_ldplayer(title):
        return

    # Ignore clicks outside LDPlayer client area
    if not (left <= x <= right and top <= y <= bottom):
        return

    win_w = right - left
    win_h = bottom - top
    if win_w <= 0 or win_h <= 0:
        return

    # Normalize → Android coordinates
    rel_x = (x - left) / win_w
    rel_y = (y - top) / win_h

    ax = int(clamp(round(rel_x * ANDROID_W), 0, ANDROID_W - 1))
    ay = int(clamp(round(rel_y * ANDROID_H), 0, ANDROID_H - 1))

    now = time.time()

    with time_lock:
        if last_tap_time is None:
            wait_before = 0
        else:
            wait_before = math.ceil(now - last_tap_time)

        last_tap_time = now

    tap_queue.put((ax, ay, wait_before))

# ---------------- MAIN ----------------
def main():
    print("🎯 LDPlayer Tap Recorder STARTED")
    print("✔ WAIT → TAP model (ceil timing)")
    print("✔ DPI-safe & client-area accurate")
    print("✔ Only ACTIVE LDPlayer window")
    print("✔ Ctrl = pause recording")
    print("✔ Ctrl+C to stop\n")

    threading.Thread(target=input_worker, daemon=True).start()

    KeyboardListener(
        on_press=on_key_press,
        on_release=on_key_release,
        daemon=True
    ).start()

    with MouseListener(on_click=on_click) as listener:
        try:
            listener.join()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
