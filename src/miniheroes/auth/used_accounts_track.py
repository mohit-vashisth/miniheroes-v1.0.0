# used_accounts_track.py
from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Set

from ..config.config import USED_ACCOUNTS_FILE


_WRITE_LOCK = threading.Lock()


def load_used_gmails() -> Set[str]:
    path = Path(USED_ACCOUNTS_FILE)
    if not path.is_file():
        return set()
    with path.open("r", encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip()}


def get_next_mailbox_index(prefix: str, domain: str = "maildrop.cc", min_index: int = 1) -> int:
    used = load_used_gmails()
    if not used:
        return max(min_index, 1)

    pattern = re.compile(
        rf"^{re.escape(prefix)}(\d+)@(?:{re.escape(domain)}|.+)$",
        re.IGNORECASE,
    )
    max_index = 0
    for email in used:
        match = pattern.match(email)
        if not match:
            continue
        try:
            max_index = max(max_index, int(match.group(1)))
        except ValueError:
            continue

    return max(max_index + 1, min_index, 1)


def save_used_gmail(email: str) -> None:
    normalized = email.strip()
    if not normalized:
        return

    path = Path(USED_ACCOUNTS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)

    with _WRITE_LOCK:
        existing = set()
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                existing = {line.strip() for line in handle if line.strip()}
        if normalized in existing:
            return

        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{normalized}\n")
