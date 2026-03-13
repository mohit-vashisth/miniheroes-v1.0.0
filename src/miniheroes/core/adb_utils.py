from __future__ import annotations

import struct
import subprocess
import time
from typing import List, Optional, Tuple

from ..core.logger import log

logger = log()


def clear_app_data(device_id: str, package_name: str) -> None:
    try:
        subprocess.run(
            ["adb", "-s", device_id, "shell", "pm", "clear", package_name],
            check=False,
            capture_output=True,
            timeout=30,
        )
        logger.info(f"[CLEAR] {device_id} {package_name}")
    except Exception as exc:
        logger.error(f"[CLEAR ERROR] {device_id}: {exc}")


def wait_for_emulator_boot(port: int, max_attempts: int = 40, delay: int = 3) -> bool:
    device_id = f"emulator-{port}"
    for attempt in range(1, max_attempts + 1):
        try:
            output = subprocess.check_output(
                ["adb", "-s", device_id, "shell", "getprop", "sys.boot_completed"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            ).strip()
            if output == "1":
                logger.info(f"[BOOT] {device_id} ready")
                return True
        except Exception:
            pass

        if attempt == 1 or attempt % 5 == 0:
            logger.info(f"[BOOT WAIT] {device_id} attempt {attempt}/{max_attempts}")
        time.sleep(delay)

    logger.error(f"[BOOT TIMEOUT] {device_id}")
    return False


def detect_running_emulator_indexes() -> List[int]:
    indexes: List[int] = []
    try:
        output = subprocess.check_output(["adb", "devices"], text=True, timeout=10)
    except Exception:
        logger.debug("[ADB] Failed to get devices list")
        return indexes

    for line in output.splitlines():
        if not line.startswith("emulator-") or "\tdevice" not in line:
            continue
        try:
            port = int(line.split("-", 1)[1].split("\t", 1)[0])
            index = (port - 5554) // 2
            if index >= 0:
                indexes.append(index)
        except (TypeError, ValueError):
            continue
    logger.debug(f"[ADB] Detected running emulator indexes: {indexes}")
    return indexes


def adb_tap(device_id: str, x: int, y: int, t: float, console_path: str) -> bool:
    logger.debug(f"[TAP] {device_id} ({x},{y}) wait={t}s")

    emulator_index: Optional[int] = None
    if device_id.startswith("emulator-"):
        try:
            port = int(device_id.split("-", 1)[1])
            emulator_index = (port - 5554) // 2
        except ValueError:
            emulator_index = None

    if emulator_index is not None:
        try:
            dn_result = subprocess.run(
                [
                    console_path,
                    "adb",
                    "--index",
                    str(emulator_index),
                    "--command",
                    f"shell input tap {x} {y}",
                ],
                check=False,
                capture_output=True,
                timeout=8,
            )
            if dn_result.returncode == 0:
                logger.debug(f"[TAP] dnconsole success for {device_id}")
                return True
        except Exception as exc:
            logger.debug(f"[TAP] dnconsole tap failed for {device_id}: {exc}")

    try:
        adb_result = subprocess.run(
            ["adb", "-s", device_id, "shell", "input", "tap", str(x), str(y)],
            check=False,
            capture_output=True,
            timeout=8,
        )
        if adb_result.returncode == 0:
            logger.debug(f"[TAP] adb success for {device_id}")
            return True
    except Exception as exc:
        logger.debug(f"[TAP] adb tap failed for {device_id}: {exc}")

    logger.error(f"[TAP FAILED] {device_id} ({x},{y})")
    return False


def verify_tap_pixel(device_id: str, x: int, y: int, timeout: float = 1.5) -> bool:
    try:
        before = _capture_raw_screenshot(device_id)
        before_pixel = _extract_pixel_rgba(before, x, y)
        if before_pixel is None:
            logger.debug(f"[VERIFY] Could not extract before pixel for {device_id}, assuming success")
            return True

        end_time = time.time() + timeout
        while time.time() < end_time:
            after = _capture_raw_screenshot(device_id)
            after_pixel = _extract_pixel_rgba(after, x, y)
            if after_pixel is None:
                logger.debug(f"[VERIFY] Could not extract after pixel for {device_id}, assuming success")
                return True
            if before_pixel != after_pixel:
                logger.debug(f"[VERIFY] Pixel changed at ({x},{y}) on {device_id}")
                return True
            time.sleep(0.1)
        logger.debug(f"[VERIFY] No pixel change detected at ({x},{y}) on {device_id}")
    except Exception as e:
        logger.debug(f"[VERIFY] Exception during verification on {device_id}: {e}")
    return True


def _capture_raw_screenshot(device_id: str) -> bytes:
    return subprocess.run(
        ["adb", "-s", device_id, "exec-out", "screencap"],
        check=False,
        capture_output=True,
        timeout=8,
    ).stdout


def _extract_pixel_rgba(data: bytes, x: int, y: int) -> Optional[Tuple[int, int, int, int]]:
    if len(data) < 12:
        return None

    width = struct.unpack("<I", data[0:4])[0]
    height = struct.unpack("<I", data[4:8])[0]
    if width <= 0 or height <= 0:
        return None
    if x < 0 or y < 0 or x >= width or y >= height:
        return None

    header_size = 12
    pixel_offset = header_size + ((y * width + x) * 4)
    if pixel_offset + 4 > len(data):
        header_size = 8
        pixel_offset = header_size + ((y * width + x) * 4)
        if pixel_offset + 4 > len(data):
            return None

    rgba = data[pixel_offset : pixel_offset + 4]
    return rgba[0], rgba[1], rgba[2], rgba[3]