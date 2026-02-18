from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Set

from ..config.config import USED_ACCOUNTS_FILE
from ..core.logger import log

logger = log()
_WRITE_LOCK = threading.Lock()


def load_used_gmails() -> Set[str]:
    path = Path(USED_ACCOUNTS_FILE)
    if not path.is_file():
        logger.debug("[ACCOUNTS] No used accounts file found, returning empty set")
        return set()

    with path.open("r", encoding="utf-8") as handle:
        emails = {line.strip() for line in handle if line.strip()}
    logger.debug(f"[ACCOUNTS] Loaded {len(emails)} used emails")
    return emails


def get_next_mailbox_index(prefix: str, domain: str = "maildrop.cc", min_index: int = 1) -> int:
    used = load_used_gmails()
    if not used:
        logger.info(f"[ACCOUNTS] No used emails, starting index = {min_index}")
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
            idx = int(match.group(1))
            if idx > max_index:
                max_index = idx
        except ValueError:
            continue

    next_index = max(max_index + 1, min_index, 1)
    logger.info(f"[ACCOUNTS] Next available mailbox index = {next_index}")
    return next_index


def save_used_gmail(email: str) -> None:
    normalized = email.strip()
    if not normalized:
        logger.warning("[ACCOUNTS] Attempted to save empty email, ignored")
        return

    path = Path(USED_ACCOUNTS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)

    with _WRITE_LOCK:
        existing = set()
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                existing = {line.strip() for line in handle if line.strip()}

        if normalized in existing:
            logger.debug(f"[ACCOUNTS] Email {normalized} already in used list, skipping")
            return

        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{normalized}\n")
        logger.success(f"Saved used email: {normalized}")