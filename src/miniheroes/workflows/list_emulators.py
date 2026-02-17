# list_emulators.py
from __future__ import annotations

import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union

from ..config.config import LD_CONSOLE, LDPLAYER_INDEXES_FILE
from ..core.adb_utils import detect_running_emulator_indexes, wait_for_emulator_boot
from ..core.emulator_tracking import get_failed_emulator_indexes, save_failed_emulator_index
from ..core.window_hide import hide_emulator_window


logger = logging.getLogger(__name__)

OUTPUT_FILE = LDPLAYER_INDEXES_FILE
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


def create_emulators(count: int):
    for _ in range(count):
        subprocess.run([LD_CONSOLE, "add"])
    print(f"LD Players: {count} | Created")


def init_ld_list() -> List[str]:
    indexes: List[str] = []
    try:
        result = subprocess.run(
            [LD_CONSOLE, "list2"],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split(",")
            if parts:
                indexes.append(parts[0])
        print("---Indexes Added---")
    except (FileNotFoundError, subprocess.CalledProcessError):
        indexes = []
    OUTPUT_FILE.write_text("\n".join(indexes), encoding="utf-8")
    return indexes


def load_indexes() -> List[str]:
    if not OUTPUT_FILE.exists():
        return []
    return [line.strip() for line in OUTPUT_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]


def delete_index(index: str) -> bool:
    indexes = load_indexes()
    if index not in indexes:
        return False
    indexes.remove(index)
    OUTPUT_FILE.write_text("\n".join(indexes), encoding="utf-8")
    return True


def pop_next_index() -> Optional[str]:
    indexes = load_indexes()
    if not indexes:
        return None
    next_index = indexes.pop(0)
    OUTPUT_FILE.write_text("\n".join(indexes), encoding="utf-8")
    return next_index


def _normalize_status(raw: str) -> str:
    lowered = raw.strip().lower()
    if lowered in {"1", "running", "true"}:
        return "running"
    return "stopped"


def _ldconsole_list2() -> List[Dict]:
    result = subprocess.run(
        [LD_CONSOLE, "list2"],
        capture_output=True,
        text=True,
        check=True,
    )
    emulators: List[Dict] = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(",")
        if len(parts) < 4:
            continue
        adb_port = 0
        if parts[3].isdigit():
            adb_port = int(parts[3])
        emulators.append(
            {
                "index": parts[0],
                "name": parts[1],
                "status": _normalize_status(parts[2]),
                "adb_port": adb_port,
            }
        )
    return emulators


def get_all_ldplayer_emulators() -> List[Dict]:
    return _ldconsole_list2()


def get_running_ldplayer_emulators() -> List[Dict]:
    return [emu for emu in _ldconsole_list2() if emu["status"] == "running"]


def get_stopped_ldplayer_emulators() -> List[Dict]:
    return [emu for emu in _ldconsole_list2() if emu["status"] == "stopped"]


def get_ldplayer_by_index(index: Union[str, int]) -> Optional[Dict]:
    target = str(index)
    for emulator in _ldconsole_list2():
        if emulator["index"] == target:
            return emulator
    return None


def get_running_emulators() -> List[str]:
    devices: List[str] = []
    for emulator in _ldconsole_list2():
        if emulator["status"] != "running":
            continue
        port = emulator["adb_port"]
        if port > 0:
            devices.append(f"127.0.0.1:{port}")
    return sorted(devices, key=lambda item: int(item.rsplit(":", 1)[-1]))


def start_emulator_indices(indices: List[Union[int, str]], sleep_sec: float = 1.5):
    for index in indices:
        subprocess.Popen(
            [LD_CONSOLE, "launch", "--index", str(index)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(sleep_sec)


def stop_emulator_indices(indices: List[Union[int, str]], sleep_sec: float = 1.0):
    for index in indices:
        subprocess.run(
            [LD_CONSOLE, "quit", "--index", str(index)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        time.sleep(sleep_sec)


def start_emulator_indices_parallel(indices: List[Union[int, str]], max_workers: int = 5):
    def _start_single(idx: Union[int, str]) -> None:
        subprocess.Popen(
            [LD_CONSOLE, "launch", "--index", str(idx)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_start_single, indices))


def stop_emulator_indices_parallel(indices: List[Union[int, str]], max_workers: int = 5):
    def _stop_single(idx: Union[int, str]) -> None:
        subprocess.run(
            [LD_CONSOLE, "quit", "--index", str(idx)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_stop_single, indices))


def list_emulator_indices() -> List[int]:
    return sorted({int(emu["index"]) for emu in _ldconsole_list2()})


def start_and_wait_for_emulators(indexes: List[int]) -> Dict[int, bool]:
    logger.info("[START] requested indexes=%s", indexes)
    if not indexes:
        return {}

    failed_indexes = get_failed_emulator_indexes()
    running_indexes = set(detect_running_emulator_indexes())
    results: Dict[int, bool] = {}

    def _start_single(idx: int) -> bool:
        if idx in failed_indexes:
            logger.warning("[START] emulator %s skipped (failed list)", idx)
            return False

        if idx in running_indexes:
            hide_emulator_window(idx, LD_CONSOLE)
            logger.info("[START] emulator %s already running", idx)
            return True

        try:
            subprocess.Popen(
                [LD_CONSOLE, "launch", "--index", str(idx)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            logger.error("[START] launch failed for emulator %s: %s", idx, exc)
            save_failed_emulator_index(idx)
            return False

        port = 5554 + (idx * 2)
        if not wait_for_emulator_boot(port):
            logger.error("[START] emulator %s boot timeout", idx)
            save_failed_emulator_index(idx)
            subprocess.run(
                [LD_CONSOLE, "quit", "--index", str(idx)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return False

        hide_emulator_window(idx, LD_CONSOLE)
        logger.info("[START] emulator %s booted", idx)
        return True

    max_workers = max(1, min(len(indexes), 8))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_start_single, idx): idx for idx in indexes}
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = bool(future.result())
            except Exception as exc:
                logger.error("[START] unexpected error for %s: %s", idx, exc)
                results[idx] = False
    return results


def close_emulators_in_parallel(indexes: List[int]):
    logger.info("[CLOSE] requested indexes=%s", indexes)
    if not indexes:
        return

    def _close_single(idx: int) -> None:
        force_result = subprocess.run(
            [LD_CONSOLE, "quit", "--index", str(idx), "--force"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if force_result.returncode != 0:
            subprocess.run(
                [LD_CONSOLE, "quit", "--index", str(idx)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    max_workers = max(1, min(len(indexes), 8))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_close_single, indexes))

    time.sleep(3)

