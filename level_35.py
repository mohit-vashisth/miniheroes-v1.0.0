# level_35.py
import os, re, html, time, subprocess, yaml, threading, concurrent.futures, random, asyncio
from typing import Optional, List
from collections import deque

from playwright.sync_api import sync_playwright
from logging_setup import logger

import vision

# ========== CONFIG ==========
LD_CONSOLE = r"D:\LDPlayer\LDPlayer9\ldconsole.exe"
GAME_PACKAGE = "com.and.brawl.en"

MY_EMULATORS = [4, 6, 7, 8]

EMAIL_SOURCE_FILE = "data/used_gmails.txt"
LEVEL_SUCCESS_FILE = "data/lvl_35.txt"
LEVEL_YAML = os.path.join("templates", "scripts", "level_35.yaml")

WORKERS = 4
CODES = ["minihero", "hero777", "mars777", "mh777", "fb7777", "vip666", "vip777", "vip888"]

# Pause / step / jump files
PAUSE_FILE = "pause.flag"
STEP_FILE  = "step.flag"
WHERE_TO_STEP_FILE = "where_to_step.txt"
FAST_RESUME_FILE = "fast_resume.flag"   # <-- NEW

email_queue = deque()
email_queue_lock = threading.Lock()

# ========== Pause logic ==========
def check_pause_or_step():
    if os.path.exists(PAUSE_FILE):
        logger.info("⏸️  Paused – delete 'pause.flag' to resume.")
        while os.path.exists(PAUSE_FILE):
            time.sleep(2)
    if os.path.exists(STEP_FILE):
        try:
            input("🔹 Step mode – Press Enter to continue to next step...")
        except (EOFError, OSError):
            logger.info("🔹 Step mode requested but no console input, continuing automatically.")

# ========== Step jump helper ==========
def get_skip_until_step() -> Optional[int]:
    """Read where_to_step.txt and return the step number to start from, or None."""
    if not os.path.exists(WHERE_TO_STEP_FILE):
        return None
    try:
        with open(WHERE_TO_STEP_FILE, "r") as f:
            num = int(f.read().strip())
        if num >= 1:
            logger.info(f"⏭️  Skipping steps until step {num} (read from {WHERE_TO_STEP_FILE})")
            return num
    except Exception:
        pass
    return None

# ========== Email queue ==========
def load_email_queue():
    already_leveled = set()
    if os.path.exists(LEVEL_SUCCESS_FILE):
        with open(LEVEL_SUCCESS_FILE, "r", encoding="utf-8") as f:
            already_leveled = {line.strip() for line in f if line.strip()}
        logger.info(f"Found {len(already_leveled)} already‑leveled emails (will skip).")
    if not os.path.exists(EMAIL_SOURCE_FILE):
        logger.error(f"Email source file not found: {EMAIL_SOURCE_FILE}")
        return False
    with open(EMAIL_SOURCE_FILE, "r", encoding="utf-8") as f:
        all_emails = [line.strip() for line in f if line.strip()]
    new_emails = [e for e in all_emails if e not in already_leveled]
    with email_queue_lock:
        email_queue.extend(new_emails)
    logger.info(f"Loaded {len(new_emails)} new emails (skipped {len(all_emails)-len(new_emails)} already leveled).")
    return True

def pop_next_email() -> Optional[str]:
    with email_queue_lock:
        if email_queue:
            return email_queue.popleft()
        return None

def save_leveled_email(email: str):
    os.makedirs(os.path.dirname(LEVEL_SUCCESS_FILE), exist_ok=True)
    with open(LEVEL_SUCCESS_FILE, "a", encoding="utf-8") as f:
        f.write(email + "\n")
    logger.info(f"[LEVELED] {email} saved.")

# ========== Emulator Launching ==========
def launch_emulator_by_index(index: int) -> bool:
    cmd = [LD_CONSOLE, "launch", "--index", str(index)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info(f"Emulator {index} launched successfully.")
            return True
        else:
            logger.error(f"Failed to launch emulator {index}: {result.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

def is_boot_completed(index: int) -> bool:
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", "shell getprop sys.boot_completed"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() == "1"
    except Exception as e:
        logger.error(f"Boot check error: {e}")
        return False

def wait_for_boot(index: int, timeout: int = 120) -> bool:
    logger.info(f"[{index}] Waiting for boot... (timeout = {timeout}s)")
    start = time.time()
    attempt = 0
    while time.time() - start < timeout:
        attempt += 1
        elapsed = int(time.time() - start)
        logger.info(f"[{index}] Boot check {attempt}... ({elapsed}s elapsed)")
        try:
            if is_boot_completed(index):
                logger.info(f"[{index}] Boot completed after {elapsed}s")
                return True
        except Exception as e:
            logger.error(f"[{index}] Boot error: {e}")
        time.sleep(2)
    logger.error(f"[{index}] Boot timeout!")
    return False

def _is_emulator_running(index: int) -> bool:
    try:
        res = subprocess.run([LD_CONSOLE, "isrunning", "--index", str(index)],
                             capture_output=True, text=True, timeout=5)
        return "running" in res.stdout.lower()
    except:
        return False

def _force_close_emulator(index: int):
    logger.info(f"[{index}] Force-closing emulator...")
    try:
        subprocess.run([LD_CONSOLE, "quit", "--index", str(index)],
                       capture_output=True, timeout=10)
    except: pass
    try:
        subprocess.run([LD_CONSOLE, "quit", "--index", str(index), "--force"],
                       capture_output=True, timeout=10)
    except: pass
    for _ in range(10):
        if not _is_emulator_running(index):
            logger.info(f"[{index}] Emulator successfully closed.")
            return
        time.sleep(1)
    logger.warning(f"[{index}] Emulator may still be running.")

def launch_game(index: int) -> bool:
    cmd = f"shell monkey -p {GAME_PACKAGE} -c android.intent.category.LAUNCHER 1"
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", cmd],
            capture_output=True, text=True, timeout=15
        )
        if "Events injected" in result.stdout:
            logger.info(f"[{index}] Game launched.")
            return True
        else:
            logger.error(f"[{index}] Launch failed: {result.stdout.strip()}")
            return False
    except Exception as e:
        logger.error(f"[{index}] Launch error: {e}")
        return False

def tap(index: int, x: int, y: int) -> bool:
    cmd = f"shell input tap {x} {y}"
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", cmd],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            logger.info(f"[{index}] Tapped ({x},{y})")
            return True
        else:
            logger.error(f"[{index}] Tap failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"[{index}] Tap error: {e}")
        return False

def type_text(index: int, text: str, clear: bool = True) -> bool:
    if clear:
        for _ in range(40):
            try:
                subprocess.run([LD_CONSOLE, "adb", "--index", str(index), "--command", "shell input keyevent 67"],
                               capture_output=True, text=True, timeout=2)
            except: pass
        for _ in range(40):
            try:
                subprocess.run([LD_CONSOLE, "adb", "--index", str(index), "--command", "shell input keyevent 112"],
                               capture_output=True, text=True, timeout=2)
            except: pass
        time.sleep(0.1)
    safe_text = text.replace(" ", "%s")
    try:
        res = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", f"shell input text {safe_text}"],
            capture_output=True, text=True, timeout=10
        )
        if res.returncode == 0:
            logger.info(f"[{index}] Text typed: {text}")
            return True
        else:
            logger.error(f"[{index}] Type failed: {res.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"[{index}] Type error: {e}")
        return False
def fetch_verification_code(email: str, timeout: int = 45) -> Optional[str]:
    local = email.split("@")[0]
    inbox_url = f"https://maildrop.cc/inbox/?mailbox={local}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page()
        try:
            page.goto(inbox_url, timeout=15000)
            logger.info(f"[MAIL] Inbox opened for {email}")
            start = time.time()
            while time.time() - start < timeout:
                # Refresh button
                try:
                    refresh_btn = page.locator('button:has-text("Refresh")')
                    if refresh_btn.count() > 0:
                        refresh_btn.click()
                except:
                    pass

                # Wait for a message
                try:
                    page.wait_for_selector("div.message", timeout=5000)
                    first_msg = page.locator("div.message").first
                    if first_msg.count() > 0:
                        first_msg.click()
                        time.sleep(1.5)   # extra time for iframe to load

                        # 1. Try iframe srcdoc
                        iframe = page.locator("iframe")
                        if iframe.count() > 0:
                            srcdoc = iframe.get_attribute("srcdoc")
                            if srcdoc:
                                unescaped = html.unescape(srcdoc)
                                m = re.search(r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4,6})", unescaped, re.IGNORECASE)
                                if m:
                                    code = m.group(1)
                                    logger.info(f"[MAIL] OTP received: {code}")
                                    browser.close()
                                    return code

                        # 2. Fallback to entire page
                        content = page.content()
                        m = re.search(r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4,6})", content, re.IGNORECASE)
                        if m:
                            code = m.group(1)
                            logger.info(f"[MAIL] OTP received: {code}")
                            browser.close()
                            return code
                except Exception:
                    pass
                time.sleep(3)
            logger.error("[MAIL] Timeout – code nahi mila")
            return None
        finally:
            browser.close()
# =========================== YAML EXECUTOR (with increased wait retries) ===========================
def execute_yaml_script(index: int, yaml_path: str, email: str, codes: Optional[List[str]] = None) -> bool:
    if codes is None:
        codes = CODES

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data.get("steps", [])
    if not steps:
        logger.error("YAML file has no steps.")
        return False

    context = {"email": email, "otp": None}
    code_index = 0

    # ---------- Step‑jump ----------
    skip_until = get_skip_until_step()   # read once at the beginning

    for step_num, step in enumerate(steps, 1):
        # If we have a jump point and haven't reached it, skip this step entirely
        if skip_until is not None and step_num < skip_until:
            continue   # completely ignore the step

        check_pause_or_step()

        step_type = list(step.keys())[0]
        params = step[step_type]
        logger.info(f"[{index}] Step {step_num}/{len(steps)}: {step_type}")

        if step_type == "wait":
            image = params["image"]
            # YAML ki retries/interval ko ignore karo – hamesha 30 retries, 0.9 sec
            retries = 30
            interval = 0.9
            confidence = params.get("confidence", 0.7)
            try:
                vision.wait_for_image(index, image, retries=retries, interval=interval, confidence=confidence)
            except TimeoutError:
                logger.error(f"[{index}] Image '{image}' not found – continuing.")

        elif step_type == "tap":
            image = params.get("image")
            x = params.get("x")
            y = params.get("y")
            # override retries/interval for image check
            retries = 30
            interval = 0.
            confidence = params.get("confidence", 0.7)
            if image:
                try:
                    vision.wait_for_image(index, image, retries=retries, interval=interval, confidence=confidence)
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
            code = fetch_verification_code(context["email"], timeout=30)
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

# ============ PROCESS ONE EMULATOR (now with fast_resume) ==============
def process_emulator_level(index: int) -> None:
    try:
        logger.info(f"\n{'='*30} Emulator {index} START {'='*30}")

        # ----- FAST RESUME MODE -----
        if os.path.exists(FAST_RESUME_FILE):
            logger.info("⚡ FAST RESUME mode active (fast_resume.flag found).")
            logger.info(f"Assuming emulator {index} is already running and at home screen.")
            input("Press Enter when ready to continue (emulator must be at home screen)...")
            # Skip all startup – go straight to email loop
        else:
            # Normal startup
            if not launch_emulator_by_index(index):
                logger.error(f"[{index}] Launch failed, skipping.")
                return
            if not wait_for_boot(index):
                _force_close_emulator(index)
                return
            if not launch_game(index):
                _force_close_emulator(index)
                return
            logger.info(f"[{index}] Waiting for start screen...")
            try:
                vision.wait_for_image(index, "starting_page.png", retries=60, interval=1.0, confidence=0.7)
                logger.info(f"[{index}] Game fully loaded.")
            except TimeoutError:
                logger.error(f"[{index}] Game load timeout – proceeding anyway.")

        # Main email processing loop
        while True:
            email = pop_next_email()
            if email is None:
                logger.info(f"[{index}] No more emails, finishing.")
                break
            logger.info(f"[{index}] Processing: {email}")
            ok = execute_yaml_script(index, LEVEL_YAML, email, codes=CODES)
            if ok:
                save_leveled_email(email)
                logger.info(f"[{index}] {email} leveled successfully.")
            else:
                logger.error(f"[{index}] {email} failed leveling.")
            time.sleep(2)

        # Close only if we started the emulator ourselves (fast resume doesn't own the emulator)
        if not os.path.exists(FAST_RESUME_FILE):
            _force_close_emulator(index)

    except Exception as e:
        logger.exception(f"[{index}] Fatal error: {e}")
        if not os.path.exists(FAST_RESUME_FILE):
            _force_close_emulator(index)

# ========== MAIN ==========
def main():
    logger.info("="*60)
    logger.info("LEVEL‑35 AUTOMATION (Login + Level Up)")
    logger.info("="*60)
    if not load_email_queue():
        return
    logger.info(f"Using emulators: {MY_EMULATORS}")
    input("Press Enter to start...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(process_emulator_level, idx) for idx in MY_EMULATORS]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Unhandled exception in task: {e}")

    logger.info("\nAll emulators processed. Exiting.")

if __name__ == "__main__":
    main()