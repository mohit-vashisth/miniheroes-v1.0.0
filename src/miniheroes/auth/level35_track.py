from __future__ import annotations

import threading
from pathlib import Path
from typing import Set

from ..config.config import DATA_DIR

LEVEL35_FILE = DATA_DIR / "level35_accounts.txt"
_WRITE_LOCK = threading.Lock()


def load_level35_accounts() -> Set[str]:
    """Return set of emails that have already reached level 35."""
    if not LEVEL35_FILE.exists():
        return set()
    with LEVEL35_FILE.open("r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_level35_account(email: str) -> None:
    """Mark an email as level‑35 completed (safe, duplicate‑aware)."""
    normalized = email.strip()
    if not normalized:
        return
    with _WRITE_LOCK:
        existing = load_level35_accounts()
        if normalized in existing:
            return
        with LEVEL35_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{normalized}\n")