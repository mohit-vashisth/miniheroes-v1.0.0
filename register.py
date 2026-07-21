# main.py
import os, json, re, html, time, subprocess, yaml, threading, concurrent.futures, random
from typing import Optional, List, Set

from playwright.sync_api import sync_playwright
from logging_setup import logger

import vision
# ========== CONFIG ==========``
LD_CONSOLE = r"D:\LDPlayer\LDPlayer9\ldconsole.exe"
APK_DIR = "apk"
APK_FILES = ["base1.apk", "base2.apk", "base3.apk"]
GAME_PACKAGE = "com.and.brawl.en"
GAME_ACTIVITY = "org.cocos2dx.javascript.AppActivity"
GMAIL_PREFIX = "355servermh"
IGNORED_EMULATOR_INDEXES = [0, 1, 2, 3, 4, 5, 6, 7, 8]
EMAIL_COUNTER_FILE = "data/email_counter.json"
USED_EMULATORS_FILE = "data/used_emulators.txt"
FAILED_EMULATORS_FILE = "data/failed_emulators.txt"
WORKERS = 4

# Locks
email_lock = threading.Lock()
used_emulators_lock = threading.Lock()

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

# ========== Emulator Serial ==========
def get_emulator_serial(index: int) -> str:
    port = 5554 + index * 2
    return f"emulator-{port}"

# ========== List all emulators ==========
def get_all_emulator_indices() -> List[int]:
    try:
        result = subprocess.run([LD_CONSOLE, "list2"], capture_output=True, text=True, timeout=10)
        indices = []
        for line in result.stdout.splitlines():
            parts = [p.strip() for p in line.split(',')]
            if parts and parts[0].isdigit():
                indices.append(int(parts[0]))
        return sorted(set(indices))
    except Exception as e:
        logger.error(f"Error reading emulator list: {e}")
        return []

# ========== Filter available indices ==========
def get_available_emulators(all_indices: List[int], ignored: List[int]) -> List[int]:
    return sorted([idx for idx in all_indices if idx not in ignored])

# ========== Used / failed tracking ==========
def load_used_emulators() -> Set[int]:
    if not os.path.exists(USED_EMULATORS_FILE):
        return set()
    with open(USED_EMULATORS_FILE, "r") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}

def save_used_emulator(index: int):
    """Thread‑safe, no duplicates."""
    with used_emulators_lock:
        if not os.path.exists(USED_EMULATORS_FILE):
            open(USED_EMULATORS_FILE, 'w').close()  # create empty file
        existing = set()
        with open(USED_EMULATORS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line.isdigit():
                    existing.add(int(line))
        if index not in existing:
            with open(USED_EMULATORS_FILE, 'a') as f:
                f.write(f"{index}\n")
            logger.info(f"[{index}] Marked as used.")
        else:
            logger.error(f"[{index}] Already in used list, skipping.")

def load_failed_emulators() -> Set[int]:
    if not os.path.exists(FAILED_EMULATORS_FILE):
        return set()
    with open(FAILED_EMULATORS_FILE, "r") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}

def save_failed_emulator(index: int):
    os.makedirs(os.path.dirname(FAILED_EMULATORS_FILE), exist_ok=True)
    with open(FAILED_EMULATORS_FILE, "a") as f:
        f.write(f"{index}\n")

# ========== Thread‑safe email generation ==========
def get_next_email(prefix: str) -> str:
    with email_lock:
        os.makedirs(os.path.dirname(EMAIL_COUNTER_FILE), exist_ok=True)
        if os.path.exists(EMAIL_COUNTER_FILE):
            with open(EMAIL_COUNTER_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"next": 1}
        next_id = data["next"]
        email = f"{prefix}{next_id}@maildrop.cc"
        data["next"] = next_id + 1
        with open(EMAIL_COUNTER_FILE, "w") as f:
            json.dump(data, f)
    logger.info(f"[EMAIL] Generated: {email}")
    return email

# ========== Check Emulator Boot ==========
def is_boot_completed(index: int) -> bool:
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", "shell getprop sys.boot_completed"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() == "1"
    except Exception as e:
        logger.error(f"something went wrong while booting: {e}")
        return False

def wait_for_boot(index: int, timeout: int = 120) -> bool:
    logger.info(f"[{index}] Waiting for boot... (timeout = {timeout}s)")
    start = time.time()
    attempt = 0
    try:
        while time.time() - start < timeout:
            attempt += 1
            elapsed = int(time.time() - start)
            logger.info(f"[{index}] Boot check {attempt}... ({elapsed}s elapsed)")
            try:
                if is_boot_completed(index):
                    logger.info(f"[{index}] Boot completed after {elapsed}s")
                    return True
            except Exception as e:
                logger.error(f"[{index}] Boot timeout!: {e}")
            time.sleep(2)
        logger.error(f"[{index}] Boot timeout!")
        return False
    except Exception as e:
        logger.error(f"[{index}] Boot check crashed: {e}")
        return False

def _is_emulator_running(index: int) -> bool:
    """Returns True if ldconsole says the emulator is running."""
    try:
        res = subprocess.run([LD_CONSOLE, "isrunning", "--index", str(index)],
                             capture_output=True, text=True, timeout=5)
        return "running" in res.stdout.lower()
    except:
        return False

def _force_close_emulator(index: int):
    """Force-close the emulator and wait until it's gone."""
    logger.info(f"[{index}] Force-closing emulator...")
    # Try normal quit first
    try:
        subprocess.run([LD_CONSOLE, "quit", "--index", str(index)],
                       capture_output=True, timeout=10)
    except:
        pass
    # Then force quit
    try:
        subprocess.run([LD_CONSOLE, "quit", "--index", str(index), "--force"],
                       capture_output=True, timeout=10)
    except:
        pass
    # Wait a bit and verify
    for _ in range(10):  # max 10 seconds wait
        if not _is_emulator_running(index):
            logger.info(f"[{index}] Emulator successfully closed.")
            return
        time.sleep(1)
    logger.warning(f"[{index}] Emulator may still be running.")

# ========== Helper: Check if app installed ==========
def is_app_installed(index: int) -> bool:
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", f"shell pm list packages {GAME_PACKAGE}"],
            capture_output=True, text=True, timeout=10
        )
        return f"package:{GAME_PACKAGE}" in result.stdout
    except Exception:
        return False

# ========== Helper: Clear Game Data ==========
def clear_game_data(index: int) -> bool:
    logger.info(f"[{index}] Clearing game data...")
    try:
        result = subprocess.run(
            [LD_CONSOLE, "adb", "--index", str(index), "--command", f"shell pm clear {GAME_PACKAGE}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 or "Success" in result.stdout:
            logger.info(f"[{index}] Game data cleared.")
            return True
        else:
            logger.error(f"[{index}] Clear data failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        logger.error(f"[{index}] Clear data error: {e}")
        return False

# ========== Main install & verify function ==========
def install_and_verify_apks(index: int, retries: int = 3) -> bool:
    if is_app_installed(index):
        logger.info(f"[{index}] Game already installed.")
        return clear_game_data(index)

    apk_paths = [os.path.join(APK_DIR, f) for f in APK_FILES]
    for path in apk_paths:
        if not os.path.isfile(path):
            logger.error(f"[{index}] APK missing: {path}")
            return False

    paths_quoted = [f'"{p}"' for p in apk_paths]
    install_cmd = f"install-multiple -r {' '.join(paths_quoted)}"

    for attempt in range(1, retries + 1):
        logger.info(f"[{index}] Install attempt {attempt}/{retries}...")
        try:
            res = subprocess.run(
                [LD_CONSOLE, "adb", "--index", str(index), "--command", install_cmd],
                capture_output=True, text=True, timeout=180
            )
        except subprocess.TimeoutExpired:
            logger.error(f"[{index}] Install timed out on attempt {attempt}")
            time.sleep(3)
            continue
        except Exception as e:
            logger.error(f"[{index}] Install error: {e}")
            time.sleep(3)
            continue

        if res.returncode != 0 and "Success" not in res.stdout:
            logger.error(f"[{index}] Install command failed: {res.stderr.strip()}")
            time.sleep(3)
            continue

        logger.info(f"[{index}] Verifying installation...")
        if is_app_installed(index):
            logger.info(f"[{index}] APKs installed successfully.")
            return clear_game_data(index)
        else:
            logger.error(f"[{index}] Package not found, will retry...")
            time.sleep(3)

    logger.error(f"[{index}] Installation failed after {retries} attempts.")
    return False

# ========== Launch Game ==========
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

# ========== ADB TYPE ==========
def type_text(index: int, text: str) -> bool:
    time.sleep(0.2)
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

# ========== ADB TAP ==========
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

# ========== FETCH CODE ==========

def fetch_verification_code(email: str, timeout: int = 30) -> Optional[str]:   # increased default timeout
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
                try:
                    refresh_btn = page.locator('button:has-text("Refresh")')
                    if refresh_btn.count() > 0:
                        refresh_btn.click()
                except: pass
                try:
                    page.wait_for_selector("div.message", timeout=5000)
                    first_msg = page.locator("div.message").first
                    if first_msg.count() > 0:
                        first_msg.click()
                        time.sleep(1)
                        iframe = page.locator("iframe")
                        if iframe.count() > 0:
                            srcdoc = iframe.get_attribute("srcdoc")
                            if srcdoc:
                                unescaped = html.unescape(srcdoc)
                                m = re.search(r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4})", unescaped, re.IGNORECASE)
                                if m:
                                    code = m.group(1)
                                    logger.info(f"[MAIL] OTP received: {code}")
                                    browser.close()
                                    return code
                        content = page.content()
                        m = re.search(r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4})", content, re.IGNORECASE)
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

# =========================== YAML EXECUTOR ===========================
def execute_yaml_script(index: int, yaml_path: str, email: str) -> bool:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data.get("steps", [])
    if not steps:
        logger.error("YAML file has no steps.")
        return False

    context = {"email": email, "otp": None}

    for step_num, step in enumerate(steps, 1):
        step_type = list(step.keys())[0]
        params = step[step_type]
        logger.info(f"[{index}] Step {step_num}/{len(steps)}: {step_type}")

        if step_type == "wait":
            image = params["image"]
            retries = params.get("retries", 45)
            confidence = params.get("confidence", 0.7)
            try:
                vision.wait_for_image(index, image, retries=retries, interval=0.5, confidence=confidence)
            except TimeoutError:
                logger.error(f"[{index}] Image '{image}' not found – continuing.")

        elif step_type == "tap":
            image = params.get("image")           # optional
            x = params.get("x")
            y = params.get("y")
            retries = params.get("retries", 2)    # retries for image confirmation
            confidence = params.get("confidence", 0.7)

            # If an image is given, wait for it (confirmation only)
            if image:
                try:
                    vision.wait_for_image(index, image, retries=retries, interval=0.5, confidence=confidence)
                    logger.info(f"[{index}] Image '{image}' found – tapping coordinates.")
                except TimeoutError:
                    logger.warning(f"[{index}] Image '{image}' not found – tapping coordinates anyway.")

            # Always tap at the provided coordinates
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

        else:
            logger.error(f"[{index}] Unknown step type '{step_type}' – skipping.")

    logger.info(f"[{index}] YAML script completed successfully.")
    return True

# ============ PROCESS ONE EMULATOR (complete lifecycle) ==============
def process_emulator(index: int) -> bool:
    emulator_launched = False  # whether we launched the emulator (so we need to close it)
    try:
        logger.info(f"\n{'='*30} Emulator {index} START {'='*30}")
        if not launch_emulator_by_index(index):
            return False
        emulator_launched = True   # now it's safe to close later

        if not wait_for_boot(index):
            return False

        logger.info(f"[{index}] Ready for install.")
        if not install_and_verify_apks(index):
            return False

        success_runs = 0
        for run_num in range(1, 5):
            logger.info(f"\n[{index}] --- Run {run_num}/4 ---")
            subprocess.run([LD_CONSOLE, "adb", "--index", str(index), "--command", f"shell am force-stop {GAME_PACKAGE}"],
                           capture_output=True, timeout=10)
            time.sleep(1)
            clear_game_data(index)

            if not launch_game(index):
                logger.error(f"[{index}] Game launch failed for run {run_num}.")
                if run_num == 1:
                    save_failed_emulator(index)
                return False

            if run_num == 1:
                save_used_emulator(index)

            logger.info(f"[{index}] Waiting for start screen...")
            try:
                vision.wait_for_image(index, "starting_page.png", retries=60, interval=1.0, confidence=0.7)
                logger.info(f"[{index}] Game fully loaded.")
            except TimeoutError:
                logger.error(f"[{index}] Game load timeout – proceeding anyway.")

            email = get_next_email(GMAIL_PREFIX)
            logger.info(f"[{index}] Using email: {email}")
            ok = execute_yaml_script(index, "templates/scripts/register.yaml", email)
            if ok:
                logger.info(f"[{index}] Run {run_num} successful!")
                with open("data/used_gmails.txt", "a") as f:
                    f.write(email + "\n")
                success_runs += 1
            else:
                logger.error(f"[{index}] Run {run_num} failed.")

        logger.info(f"[{index}] Finished: {success_runs}/4 successful")
        return success_runs >= 3

    except Exception as e:
        logger.exception(f"[{index}] Unexpected error: {e}")
        return False

    finally:
        if emulator_launched:
            # Forcefully close the emulator (and its window) if it was started
            try:
                _force_close_emulator(index)
                logger.info(f"[{index}] Emulator closed (force).")
            except Exception:
                # last resort: normal quit
                try:
                    subprocess.run([LD_CONSOLE, "quit", "--index", str(index)],
                                   capture_output=True, timeout=10)
                    logger.info(f"[{index}] Emulator closed.")
                except Exception:
                    logger.error(f"[{index}] Could not close emulator.")

# =====================================================================
# MAIN – BATCH PARALLEL EXECUTION
# =====================================================================
def main():
    logger.info("="*60)
    logger.info("MINIHEROES AUTOMATION (Parallel Worker Pool)")
    logger.info("="*60)

    all_idx = get_all_emulator_indices()
    if not all_idx:
        logger.error("No emulators found via list2. Exiting.")
        return

    used = load_used_emulators()
    failed = load_failed_emulators()
    ignored = set(IGNORED_EMULATOR_INDEXES)

    remaining = [idx for idx in all_idx if idx not in used and idx not in failed and idx not in ignored]
    if not remaining:
        logger.error("All emulators processed or ignored.")
        return

    logger.info(f"Total remaining emulators: {len(remaining)}")
    logger.info(f"Ignored: {IGNORED_EMULATOR_INDEXES}")
    input("Press Enter to start...")

    # Submit all tasks to a fixed-size pool (4 workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        future_to_idx = {executor.submit(process_emulator, idx): idx for idx in remaining}
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                success = future.result()
            except Exception as e:
                logger.error(f"[{idx}] Exception: {e}")
                success = False
            if not success:
                # mark failed only if not already used
                if idx not in load_used_emulators():
                    save_failed_emulator(idx)
                    logger.error(f"[{idx}] Marked as failed.")
            # Used emulators are saved inside process_emulator

    logger.info("\nAll emulators processed. Exiting.")
if __name__ == "__main__":
    main()