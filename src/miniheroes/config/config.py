# config.py
import os
from pathlib import Path

# ==================== PROJECT PATHS ====================
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
MINIHEROES_DIR = SRC_DIR / "miniheroes"
DATA_DIR = MINIHEROES_DIR / "data"
APK_DIR = MINIHEROES_DIR / "apk"
ASSETS_APK_DIR = PROJECT_ROOT / "assets" / "apk"
LDPLAYER_INDEXES_FILE = DATA_DIR / "ldplayer_indexes.txt"
TAP_STEPS_FILE = DATA_DIR / "tap_steps.txt"

# ==================== LDPLAYER PATHS ====================
def _resolve_ld_console() -> Path:
    env_override = os.getenv("LDPLAYER_CONSOLE") or os.getenv("LD_CONSOLE")
    if env_override:
        override_path = Path(env_override).expanduser()
        if override_path.exists():
            return override_path

    drives = ["C:", "D:", "E:"]
    candidates = []
    for drive in drives:
        candidates.extend(
            [
                Path(f"{drive}/LDPlayer/LDPlayer9/ldconsole.exe"),
                Path(f"{drive}/LDPlayer/LDPlayer9/dnconsole.exe"),
                Path(f"{drive}/Program Files/LDPlayer/LDPlayer9/ldconsole.exe"),
                Path(f"{drive}/Program Files/LDPlayer/LDPlayer9/dnconsole.exe"),
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return Path("ldconsole.exe")


LD_CONSOLE = str(_resolve_ld_console())

# ==================== FILES ====================
USED_EMU_FILE = DATA_DIR / "emulator_index_used.txt"
FAILED_EMU_FILE = DATA_DIR / "emulator_index_failed.txt"
USED_ACCOUNTS_FILE = DATA_DIR / "used_accounts.txt"
LOG_FILE = PROJECT_ROOT / "automation_log.txt"

# ==================== GAME CONFIG ====================
GAME_PACKAGE = "com.and.brawl.en"
BASE_NAME = "9wayroad"

# ==================== APK FILES ====================
APK_FILES = ["1.apk", "2.apk", "3.apk"]

def get_apk_paths() -> list[Path]:
    primary_paths = [APK_DIR / name for name in APK_FILES]
    fallback_paths = [ASSETS_APK_DIR / name for name in APK_FILES]

    if all(path.exists() for path in primary_paths):
        return primary_paths
    if all(path.exists() for path in fallback_paths):
        return fallback_paths

    return primary_paths

# ==================== BATCH CONFIG ====================
BATCH_SIZE = 4
MAX_EMULATORS = 999

# ==================== TAP VERIFICATION ====================
VERIFY_TAPS = False
VERIFY_TIMEOUT = 1.5
VERIFY_RETRY_DELAY = 0.3

# ==================== CREATE DIRS IF NOT EXIST ====================
DATA_DIR.mkdir(parents=True, exist_ok=True)
APK_DIR.mkdir(parents=True, exist_ok=True)
