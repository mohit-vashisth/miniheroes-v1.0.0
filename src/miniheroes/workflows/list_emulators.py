from __future__ import annotations

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union

from ..config.config import LD_CONSOLE, LDPLAYER_INDEXES_FILE
from ..core.adb_utils import detect_running_emulator_indexes, wait_for_emulator_boot
from ..core.emulator_tracking import get_failed_emulator_indexes, save_failed_emulator_index
from ..core.logger import log
from ..core.window_hide import hide_emulator_window


logger = log()

OUTPUT_FILE = LDPLAYER_INDEXES_FILE
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)


def create_emulators(count: int):
    """Create new LDPlayer emulators"""
    logger.info(f"[CREATE] Creating {count} new emulator(s)")
    for i in range(count):
        subprocess.run([LD_CONSOLE, "add"])
        logger.debug(f"[CREATE] Created emulator {i+1}/{count}")
    logger.success(f"Created {count} new LDPlayer emulator(s)")


def init_ld_list() -> List[str]:
    """Initialize the emulator index list file"""
    logger.info("[INIT] Initializing emulator index list")
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
        logger.info(f"[INIT] Found {len(indexes)} emulator(s)")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logger.error(f"[INIT] Failed to get emulator list: {e}")
        indexes = []

    OUTPUT_FILE.write_text("\n".join(indexes), encoding="utf-8")
    logger.debug(f"[INIT] Saved {len(indexes)} indexes to {OUTPUT_FILE}")
    return indexes


def load_indexes() -> List[str]:
    """Load emulator indexes from file"""
    if not OUTPUT_FILE.exists():
        logger.debug("[LOAD] No index file found")
        return []

    indexes = [line.strip() for line in OUTPUT_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    logger.debug(f"[LOAD] Loaded {len(indexes)} indexes from file")
    return indexes


def delete_index(index: str) -> bool:
    """Delete an index from the list file"""
    logger.debug(f"[DELETE] Attempting to delete index {index}")
    indexes = load_indexes()
    if index not in indexes:
        logger.warning(f"[DELETE] Index {index} not found in list")
        return False

    indexes.remove(index)
    OUTPUT_FILE.write_text("\n".join(indexes), encoding="utf-8")
    logger.info(f"[DELETE] Removed index {index} from list")
    return True


def pop_next_index() -> Optional[str]:
    """Pop the next available index from the list"""
    indexes = load_indexes()
    if not indexes:
        logger.debug("[POP] No indexes available")
        return None

    next_index = indexes.pop(0)
    OUTPUT_FILE.write_text("\n".join(indexes), encoding="utf-8")
    logger.debug(f"[POP] Next index: {next_index}")
    return next_index


def _normalize_status(raw: str) -> str:
    """Normalize status string from ldconsole"""
    lowered = raw.strip().lower()
    if lowered in {"1", "running", "true"}:
        return "running"
    return "stopped"


def _ldconsole_list2() -> List[Dict]:
    """Get detailed emulator list from ldconsole"""
    logger.debug("[LD] Fetching emulator list from ldconsole")
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

        emulator = {
            "index": parts[0],
            "name": parts[1],
            "status": _normalize_status(parts[2]),
            "adb_port": adb_port,
        }
        emulators.append(emulator)

    logger.debug(f"[LD] Found {len(emulators)} emulators")
    return emulators


def get_all_ldplayer_emulators() -> List[Dict]:
    """Get all LDPlayer emulators"""
    return _ldconsole_list2()


def get_running_ldplayer_emulators() -> List[Dict]:
    """Get running LDPlayer emulators"""
    running = [emu for emu in _ldconsole_list2() if emu["status"] == "running"]
    logger.debug(f"[LD] Running emulators: {[e['index'] for e in running]}")
    return running


def get_stopped_ldplayer_emulators() -> List[Dict]:
    """Get stopped LDPlayer emulators"""
    stopped = [emu for emu in _ldconsole_list2() if emu["status"] == "stopped"]
    logger.debug(f"[LD] Stopped emulators: {[e['index'] for e in stopped]}")
    return stopped


def get_ldplayer_by_index(index: Union[str, int]) -> Optional[Dict]:
    """Get emulator info by index"""
    target = str(index)
    for emulator in _ldconsole_list2():
        if emulator["index"] == target:
            logger.debug(f"[LD] Found emulator {target}")
            return emulator
    logger.debug(f"[LD] Emulator {target} not found")
    return None


def get_running_emulators() -> List[str]:
    """Get list of running emulator ADB addresses"""
    devices: List[str] = []
    for emulator in _ldconsole_list2():
        if emulator["status"] != "running":
            continue
        port = emulator["adb_port"]
        if port > 0:
            devices.append(f"127.0.0.1:{port}")

    sorted_devices = sorted(devices, key=lambda item: int(item.rsplit(":", 1)[-1]))
    logger.debug(f"[LD] Running ADB devices: {sorted_devices}")
    return sorted_devices


def start_emulator_indices(indices: List[Union[int, str]], sleep_sec: float = 1.5):
    """Start emulators sequentially"""
    logger.info(f"[START] Starting {len(indices)} emulator(s) sequentially: {indices}")
    for i, index in enumerate(indices, 1):
        logger.debug(f"[START] Starting emulator {index} ({i}/{len(indices)})")
        subprocess.Popen(
            [LD_CONSOLE, "launch", "--index", str(index)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(sleep_sec)
    logger.debug("[START] All start commands sent")


def stop_emulator_indices(indices: List[Union[int, str]], sleep_sec: float = 1.0):
    """Stop emulators sequentially"""
    logger.info(f"[STOP] Stopping {len(indices)} emulator(s) sequentially: {indices}")
    for i, index in enumerate(indices, 1):
        logger.debug(f"[STOP] Stopping emulator {index} ({i}/{len(indices)})")
        subprocess.run(
            [LD_CONSOLE, "quit", "--index", str(index)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        time.sleep(sleep_sec)
    logger.debug("[STOP] All stop commands sent")


def start_emulator_indices_parallel(indices: List[Union[int, str]], max_workers: int = 5):
    """Start emulators in parallel"""
    logger.info(f"[START] Starting {len(indices)} emulator(s) in parallel with {max_workers} workers")

    def _start_single(idx: Union[int, str]) -> None:
        logger.debug(f"[START] Starting emulator {idx}")
        subprocess.Popen(
            [LD_CONSOLE, "launch", "--index", str(idx)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_start_single, indices))
    logger.debug("[START] All parallel start commands sent")


def stop_emulator_indices_parallel(indices: List[Union[int, str]], max_workers: int = 5):
    """Stop emulators in parallel"""
    logger.info(f"[STOP] Stopping {len(indices)} emulator(s) in parallel with {max_workers} workers")

    def _stop_single(idx: Union[int, str]) -> None:
        logger.debug(f"[STOP] Stopping emulator {idx}")
        subprocess.run(
            [LD_CONSOLE, "quit", "--index", str(idx)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_stop_single, indices))
    logger.debug("[STOP] All parallel stop commands sent")


def list_emulator_indices() -> List[int]:
    """Get sorted list of all emulator indices"""
    indices = sorted({int(emu["index"]) for emu in _ldconsole_list2()})
    logger.debug(f"[LD] All emulator indices: {indices}")
    return indices


def start_and_wait_for_emulators(indexes: List[int]) -> Dict[int, bool]:
    """Start emulators and wait for them to boot"""
    logger.info(f"[START] Requested indexes: {indexes}")
    if not indexes:
        logger.warning("[START] No indexes provided")
        return {}

    failed_indexes = get_failed_emulator_indexes()
    running_indexes = set(detect_running_emulator_indexes())

    logger.debug(f"[START] Already running: {sorted(running_indexes)}")
    logger.debug(f"[START] Failed list: {sorted(failed_indexes)}")

    results: Dict[int, bool] = {}

    def _start_single(idx: int) -> bool:
        logger.debug(f"[START] Processing emulator {idx}")

        if idx in failed_indexes:
            logger.warning(f"[START] Emulator {idx} skipped (in failed list)")
            return False

        if idx in running_indexes:
            logger.info(f"[START] Emulator {idx} already running")
            hide_emulator_window(idx, LD_CONSOLE)
            return True

        # Launch the emulator
        logger.info(f"[START] Launching emulator {idx}")
        try:
            subprocess.Popen(
                [LD_CONSOLE, "launch", "--index", str(idx)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            logger.error(f"[START] Launch failed for emulator {idx}: {exc}")
            save_failed_emulator_index(idx)
            return False

        # Wait for boot
        port = 5554 + (idx * 2)
        logger.info(f"[START] Waiting for emulator {idx} to boot (port {port})")
        if not wait_for_emulator_boot(port):
            logger.error(f"[START] Emulator {idx} boot timeout")
            save_failed_emulator_index(idx)
            # Try to quit the emulator
            subprocess.run(
                [LD_CONSOLE, "quit", "--index", str(idx)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return False

        # Hide window after successful boot
        hide_emulator_window(idx, LD_CONSOLE)
        logger.success(f"Emulator {idx} started and booted successfully")
        return True

    # Start emulators in parallel
    max_workers = max(1, min(len(indexes), 8))
    logger.info(f"[START] Starting {len(indexes)} emulator(s) in parallel with {max_workers} workers")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_start_single, idx): idx for idx in indexes}

        completed = 0
        for future in as_completed(future_map):
            completed += 1
            idx = future_map[future]
            try:
                results[idx] = bool(future.result())
            except Exception as exc:
                logger.error(f"[START] Unexpected error for emulator {idx}: {exc}")
                results[idx] = False
            logger.progress(completed, len(indexes), f"Emulator {idx}")

    successful = [idx for idx, success in results.items() if success]
    failed = [idx for idx, success in results.items() if not success]

    logger.info(f"[START] Results: {len(successful)} successful, {len(failed)} failed")
    if successful:
        logger.success(f"Successfully started: {successful}")
    if failed:
        logger.fail(f"Failed to start: {failed}")

    return results


def close_emulators_in_parallel(indexes: List[int]):
    """Close multiple emulators in parallel"""
    logger.info(f"[CLOSE] Closing {len(indexes)} emulator(s) in parallel")
    if not indexes:
        logger.debug("[CLOSE] No indexes to close")
        return

    def _close_single(idx: int) -> None:
        logger.debug(f"[CLOSE] Closing emulator {idx}")
        # Try force quit first
        force_result = subprocess.run(
            [LD_CONSOLE, "quit", "--index", str(idx), "--force"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if force_result.returncode != 0:
            # Fallback to normal quit
            subprocess.run(
                [LD_CONSOLE, "quit", "--index", str(idx)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    max_workers = max(1, min(len(indexes), 8))
    logger.debug(f"[CLOSE] Using {max_workers} workers")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_close_single, indexes))

    logger.success(f"Closed {len(indexes)} emulator(s)")
    time.sleep(3)  # Wait for resources to free