# taps_recorder.py

OUTPUT_FILE = r"E:\Github\miniheroes-v1.0.0\src\miniheroes\data\tap_steps.txt"

# ---------------- DPI AWARE ----------------
try:
    import ctypes
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# ---------------- IMPORTS ----------------
import sys
import time
import threading
import queue
from pynput.mouse import Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener, Key
import pygetwindow as gw

try:
    import win32gui
    WIN32_OK = True
except Exception:
    WIN32_OK = False

# ---------------- CONFIG ----------------
ANDROID_W = 720
ANDROID_H = 1280

LDPLAYER_KEYWORDS = ["ldplayer", "a1", "a2", "a3", "a4", "a"]
DEBUG = "--debug" in sys.argv

# ---------------- STATE ----------------
tap_queue = queue.Queue()
ctrl_pressed = False
pending_tap = None
time_lock = threading.Lock()

# ---------------- HELPERS ----------------
def append_to_file(line):
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def window_matches_ldplayer(title):
    if not title:
        return False
    title = title.lower()
    return any(k in title for k in LDPLAYER_KEYWORDS)

def get_client_rect(hwnd):
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

# ---------------- FILE WRITER ----------------
def input_worker():

    while True:

        x, y, wait_time = tap_queue.get()

        line = f"({x}, {y}, {wait_time})"

        append_to_file(line)

        print("SAVED:", line)

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

# ---------------- MOUSE ----------------
def on_click(x, y, button, pressed):

    global pending_tap

    if not pressed:
        return

    if ctrl_pressed:
        return

    info = get_foreground_window_info()

    if not info:
        return

    hwnd, title, left, top, right, bottom, is_min = info

    if is_min:
        return

    if not window_matches_ldplayer(title):
        return

    if not (left <= x <= right and top <= y <= bottom):
        return

    win_w = right - left
    win_h = bottom - top

    if win_w <= 0 or win_h <= 0:
        return

    rel_x = (x - left) / win_w
    rel_y = (y - top) / win_h

    ax = int(rel_x * ANDROID_W)
    ay = int(rel_y * ANDROID_H)

    now = time.time()

    with time_lock:

        if pending_tap is not None:

            px, py, pt = pending_tap #type: ignore
            wait_after = round(now - pt, 2)

            tap_queue.put((px, py, wait_after))

            print(f"TAP: ({px},{py}) wait_after={wait_after}")

        pending_tap = (ax, ay, now)

# ---------------- FLUSH LAST TAP ----------------
def flush_last_tap():

    global pending_tap

    if pending_tap:

        x, y, _ = pending_tap

        tap_queue.put((x, y, 0))

        print(f"TAP: ({x},{y}) wait_after=0")

# ---------------- MAIN ----------------
def main():

    print("\nLDPlayer TAP RECORDER STARTED")
    print("TAP → WAIT model")
    print("Click inside LDPlayer window")
    print("Ctrl = pause")
    print("Ctrl+C = stop\n")

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
            flush_last_tap()


if __name__ == "__main__":
    main()