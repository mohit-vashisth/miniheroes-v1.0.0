from __future__ import annotations

import threading
from pathlib import Path
from typing import Set

from ..config.config import FAILED_EMU_FILE, USED_EMU_FILE
from ..core.logger import log

logger = log()
_USED_LOCK = threading.Lock()
_FAILED_LOCK = threading.Lock()


def save_used_emulator_index(index: int) -> None:
    _append_index_to_file(index, Path(USED_EMU_FILE), _USED_LOCK)
    logger.info(f"[TRACK] Marked emulator {index} as USED")


def save_failed_emulator_index(index: int) -> None:
    _append_index_to_file(index, Path(FAILED_EMU_FILE), _FAILED_LOCK)
    logger.warning(f"[TRACK] Marked emulator {index} as FAILED")


def get_used_emulator_indexes() -> Set[int]:
    used = _load_indexes_from_file(Path(USED_EMU_FILE))
    logger.debug(f"[TRACK] Loaded {len(used)} used emulators: {sorted(used)}")
    return used


def get_failed_emulator_indexes() -> Set[int]:
    failed = _load_indexes_from_file(Path(FAILED_EMU_FILE))
    logger.debug(f"[TRACK] Loaded {len(failed)} failed emulators: {sorted(failed)}")
    return failed


def _append_index_to_file(index: int, file_path: Path, lock: threading.Lock) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with lock:
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{index}\n")
        logger.debug(f"[TRACK] Appended {index} to {file_path.name}")


def _load_indexes_from_file(file_path: Path) -> Set[int]:
    if not file_path.exists():
        logger.debug(f"[TRACK] File {file_path.name} does not exist, returning empty set")
        return set()

    indexes: Set[int] = set()
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if value.isdigit():
                indexes.add(int(value))
    logger.debug(f"[TRACK] Loaded {len(indexes)} indexes from {file_path.name}")
    return indexes


def mark_running_emulators_as_used():
    """Detect currently running emulators and mark them as used (if not already)."""
    logger.info("[TRACK] Checking for running emulators to mark as used")
    from .adb_utils import detect_running_emulator_indexes

    running = detect_running_emulator_indexes()
    if not running:
        logger.debug("[TRACK] No running emulators found")
        return

    used = get_used_emulator_indexes()
    failed = get_failed_emulator_indexes()
    marked = 0

    for idx in running:
        if idx not in used and idx not in failed:
            save_used_emulator_index(idx)
            marked += 1
            logger.info(f"[TRACK] Running emulator {idx} marked as used (will be skipped)")

    if marked > 0:
        logger.success(f"Marked {marked} running emulator(s) as used")
    else:
        logger.debug("[TRACK] No new running emulators to mark")