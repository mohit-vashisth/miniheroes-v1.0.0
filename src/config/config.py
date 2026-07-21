# src/config/config.py
import os

# ======================== BASE DIRECTORIES ========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # src/
ROOT_DIR = os.path.dirname(BASE_DIR)                                     # project root

# ======================== DATA ======================================
DATA_DIR = os.path.join(BASE_DIR, "data")
EMAIL_COUNTER_FILE = os.path.join(DATA_DIR, "email_counter.json")
USED_EMULATORS_FILE = os.path.join(DATA_DIR, "used_emulators.txt")
FAILED_EMULATORS_FILE = os.path.join(DATA_DIR, "failed_emulators.txt")
EMAIL_SOURCE_FILE = os.path.join(DATA_DIR, "used_gmails.txt")
LEVEL_SUCCESS_FILE = os.path.join(DATA_DIR, "lvl_35.txt")

# ======================== APK ======================================
APK_DIR = os.path.join(BASE_DIR, "apk")   # now inside src/apk/
APK_FILES = ["base1.apk", "base2.apk", "base3.apk"]

# ======================== TEMPLATES =================================
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
CROPS_DIR = os.path.join(TEMPLATES_DIR, "crops")
SCRIPTS_DIR = os.path.join(TEMPLATES_DIR, "scripts")
REGISTER_YAML = os.path.join(SCRIPTS_DIR, "register.yaml")
LEVEL_35_YAML = os.path.join(SCRIPTS_DIR, "level_35.yaml")

# ======================== TOOLS =====================================
# Tools are now in src/tools/ — used by template_tool.py, not by main scripts

# ======================== PAUSE / STEP FLAGS (still at root) ========
PAUSE_FILE = os.path.join(ROOT_DIR, "pause.flag")
STEP_FILE = os.path.join(ROOT_DIR, "step.flag")
WHERE_TO_STEP_FILE = os.path.join(ROOT_DIR, "where_to_step.txt")
FAST_RESUME_FILE = os.path.join(ROOT_DIR, "fast_resume.flag")

# ======================== LDPlayer / ADB ============================
LD_CONSOLE = r"D:\LDPlayer\LDPlayer9\ldconsole.exe"
ADB_PATH = r"D:\LDPlayer\LDPlayer9\adb.exe"

# ======================== GAME ======================================
GAME_PACKAGE = "com.and.brawl.en"
GAME_ACTIVITY = "org.cocos2dx.javascript.AppActivity"

# ======================== EMULATORS =================================
MY_EMULATORS = [4, 6, 7, 8]
IGNORED_EMULATOR_INDEXES = [0, 1, 2, 3, 4, 5, 6, 7, 8]

# ======================== EMAIL / ACCOUNTS ==========================
GMAIL_PREFIX = "355servermh"
CODES = ["minihero", "hero777", "mars777", "mh777", "fb7777", "vip666", "vip777", "vip888"]

# ======================== WORKERS ===================================
WORKERS = 4

# ======================== TIMEOUTS / RETRIES ========================
BOOT_TIMEOUT = 120
GAME_LAUNCH_TIMEOUT = 15
ADB_TAP_TIMEOUT = 5
ADB_TYPE_TIMEOUT = 10
INSTALL_TIMEOUT = 180
OTP_TIMEOUT = 45