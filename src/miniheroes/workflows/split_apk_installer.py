from __future__ import annotations

import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from ..config.config import APK_FILES, APK_DIR, GAME_PACKAGE, get_apk_paths
from ..core.logger import log
from ..core.emulator_tracking import save_used_emulator_index   # <-- added import

logger = log()


def install_split_apks(device_id: str) -> List[str]:
    """Install split APKs on a single device using install-multiple"""
    logger.info(f"[INSTALL] Installing split APKs on {device_id}")

    apk_paths = [str(path) for path in get_apk_paths()]
    if not apk_paths:
        logger.error("[INSTALL] No APK files configured")
        raise FileNotFoundError("No APK files configured.")

    # Check if all APK files exist
    for path in apk_paths:
        if not os.path.isfile(path):
            logger.error(f"[INSTALL] Missing APK file: {path}")
            raise FileNotFoundError(f"Missing APK file: {path}")

    logger.debug(f"[INSTALL] APK paths: {apk_paths}")

    # Install using install-multiple
    command = ["adb", "-s", device_id, "install-multiple", "-r", *apk_paths]
    logger.debug(f"[INSTALL] Running command: {' '.join(command)}")

    try:
        subprocess.check_call(command)
        logger.success(f"Installed APKs on {device_id}: {', '.join(APK_FILES)}")
        return apk_paths
    except subprocess.CalledProcessError as e:
        logger.error(f"[INSTALL] Failed to install APKs on {device_id}: {e}")
        raise


def is_app_installed(device_id: str, package_name: str) -> bool:
    """Check if app is installed on device"""
    logger.debug(f"[CHECK] Checking if {package_name} is installed on {device_id}")

    try:
        output = subprocess.check_output(
            ["adb", "-s", device_id, "shell", "pm", "list", "packages", package_name],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
        installed = f"package:{package_name}" in output
        if installed:
            logger.debug(f"[CHECK] {package_name} is installed on {device_id}")
        else:
            logger.debug(f"[CHECK] {package_name} is NOT installed on {device_id}")
        return installed
    except subprocess.TimeoutExpired:
        logger.warning(f"[CHECK] Timeout checking installation on {device_id}")
        return False
    except Exception as e:
        logger.debug(f"[CHECK] Error checking installation on {device_id}: {e}")
        return False


def launch_app_e(device_id: str, package: str, wait: float = 3.0):
    """Launch app on device using monkey command"""
    logger.info(f"[LAUNCH] Launching {package} on {device_id} (wait {wait}s)")

    try:
        subprocess.run(
            [
                "adb",
                "-s",
                device_id,
                "shell",
                "monkey",
                "-p",
                package,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        logger.debug(f"[LAUNCH] Launch command sent, waiting {wait}s for app to load")
        time.sleep(wait)
        logger.debug(f"[LAUNCH] App launched on {device_id}")
    except Exception as e:
        logger.error(f"[LAUNCH] Failed to launch app on {device_id}: {e}")
        # Still wait even if launch command failed
        time.sleep(wait)


def install_apk_on_device(device_id: str, emulator_index: int) -> bool:
    """Install APKs on a single device with error handling and mark emulator as used on success"""
    logger.info(f"[INSTALL] Installing APKs on {device_id} for emulator {emulator_index}")

    try:
        install_split_apks(device_id)
        # Mark emulator as used immediately after successful installation
        save_used_emulator_index(emulator_index)
        logger.success(f"APK installation successful on {device_id}, emulator {emulator_index} marked used")
        return True
    except Exception as exc:
        logger.error(f"[INSTALL] Failed on {device_id}: {exc}")
        return False


def install_apks_in_parallel(indexes: List[int]) -> List[int]:
    """Install APKs on multiple emulators in parallel"""
    if not indexes:
        logger.debug("[INSTALL] No indexes to install on")
        return []

    logger.info(f"[INSTALL] Starting parallel installation on {len(indexes)} emulators: {indexes}")
    successful_indexes: List[int] = []

    def _install_single(idx: int):
        device_id = f"emulator-{5554 + (idx * 2)}"
        logger.debug(f"[INSTALL] Processing emulator {idx} ({device_id})")

        # Check if already installed
        if is_app_installed(device_id, GAME_PACKAGE):
            logger.info(f"[INSTALL] Emulator {idx} already has {GAME_PACKAGE} installed")
            # Optional: mark as used even if already installed (uncomment if desired)
            # save_used_emulator_index(idx)
            return idx, True

        # Install APKs
        logger.info(f"[INSTALL] Installing on emulator {idx}")
        success = install_apk_on_device(device_id, idx)   # <-- pass index
        return idx, success

    # Run installations in parallel
    max_workers = max(1, min(len(indexes), 8))
    logger.info(f"[INSTALL] Using {max_workers} parallel workers")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_install_single, idx): idx for idx in indexes}

        completed = 0
        for future in as_completed(future_map):
            completed += 1
            idx = future_map[future]
            try:
                result_idx, ok = future.result()
                if ok:
                    successful_indexes.append(result_idx)
                    logger.progress(completed, len(indexes), f"Emulator {idx} ✓")
                else:
                    logger.progress(completed, len(indexes), f"Emulator {idx} ✗")
            except Exception as exc:
                logger.error(f"[INSTALL] Unexpected failure on emulator {idx}: {exc}")
                logger.progress(completed, len(indexes), f"Emulator {idx} ✗")

    # Reorder results to match input order
    ordered_success = [idx for idx in indexes if idx in set(successful_indexes)]

    # Summary
    success_count = len(ordered_success)
    if success_count == len(indexes):
        logger.success(f"APK installation successful on all {success_count} emulators")
    elif success_count > 0:
        logger.info(f"[INSTALL] Success: {success_count}/{len(indexes)} emulators")
        if success_count < len(indexes):
            failed = [idx for idx in indexes if idx not in ordered_success]
            logger.warning(f"[INSTALL] Failed on: {failed}")
    else:
        logger.error(f"[INSTALL] APK installation failed on all {len(indexes)} emulators")

    return ordered_success