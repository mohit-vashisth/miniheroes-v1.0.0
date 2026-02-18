# split_apk_installer.py
from __future__ import annotations

import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from ..config.config import APK_FILES, APK_DIR, GAME_PACKAGE, get_apk_paths


logger = logging.getLogger(__name__)


def install_split_apks(device_id: str) -> List[str]:
    apk_paths = [str(path) for path in get_apk_paths()]
    if not apk_paths:
        raise FileNotFoundError("No APK files configured.")

    for path in apk_paths:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Missing APK file: {path}")

    command = ["adb", "-s", device_id, "install-multiple", "-r", *apk_paths]
    subprocess.check_call(command)
    print(f"[OK] Installed APKs on {device_id}: {', '.join(APK_FILES)} from {APK_DIR}")
    return apk_paths


def is_app_installed(device_id: str, package_name: str) -> bool:
    try:
        output = subprocess.check_output(
            ["adb", "-s", device_id, "shell", "pm", "list", "packages", package_name],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
        return f"package:{package_name}" in output
    except Exception:
        return False


def launch_app_e(device_id: str, package: str, wait: float = 32.0):
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
    )
    time.sleep(wait)


def install_apk_on_device(device_id: str) -> bool:
    try:
        install_split_apks(device_id)
        return True
    except Exception as exc:
        logger.error("[INSTALL] failed on %s: %s", device_id, exc)
        return False


def install_apks_in_parallel(indexes: List[int]) -> List[int]:
    if not indexes:
        return []

    logger.info("[INSTALL] parallel start for indexes=%s", indexes)
    successful_indexes: List[int] = []

    def _install_single(idx: int):
        device_id = f"emulator-{5554 + (idx * 2)}"
        if is_app_installed(device_id, GAME_PACKAGE):
            logger.info("[INSTALL] emulator %s already has %s", idx, GAME_PACKAGE)
            return idx, True
        return idx, install_apk_on_device(device_id)

    max_workers = max(1, min(len(indexes), 8))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_install_single, idx): idx for idx in indexes}
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                result_idx, ok = future.result()
                if ok:
                    successful_indexes.append(result_idx)
            except Exception as exc:
                logger.error("[INSTALL] unexpected failure on emulator %s: %s", idx, exc)

    ordered_success = [idx for idx in indexes if idx in set(successful_indexes)]
    logger.info("[INSTALL] success=%s/%s", len(ordered_success), len(indexes))
    return ordered_success

