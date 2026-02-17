# emulator_tracking.py
from __future__ import annotations

import threading
from pathlib import Path
from typing import Set

from ..config.config import FAILED_EMU_FILE, USED_EMU_FILE


_USED_LOCK = threading.Lock()
_FAILED_LOCK = threading.Lock()


def save_used_emulator_index(index: int) -> None:
    _append_index_to_file(index, Path(USED_EMU_FILE), _USED_LOCK)


def save_failed_emulator_index(index: int) -> None:
    _append_index_to_file(index, Path(FAILED_EMU_FILE), _FAILED_LOCK)


def get_used_emulator_indexes() -> Set[int]:
    return _load_indexes_from_file(Path(USED_EMU_FILE))


def get_failed_emulator_indexes() -> Set[int]:
    return _load_indexes_from_file(Path(FAILED_EMU_FILE))


def _append_index_to_file(index: int, file_path: Path, lock: threading.Lock) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with lock:
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{index}\n")


def _load_indexes_from_file(file_path: Path) -> Set[int]:
    if not file_path.exists():
        return set()

    indexes: Set[int] = set()
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if value.isdigit():
                indexes.add(int(value))
    return indexes
