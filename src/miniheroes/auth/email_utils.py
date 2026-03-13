# email_utils.py
from __future__ import annotations

import time
from typing import List, Optional

from .gmail_codes import fetch_verification_code, generate_mailboxes
from .used_accounts_track import get_next_mailbox_index, load_used_gmails

# Import the default logger
from ..core.logger import log

logger = log()  # returns the single project-wide logger


def generate_fresh_emails(base_name: str, count: int, domain: str = "maildrop.cc") -> List[str]:
    start_index = get_next_mailbox_index(base_name, domain=domain, min_index=1)
    emails = generate_mailboxes(base_name, count, start_index=start_index)
    logger.info(f"[EMAIL] Generated {count} fresh emails with base '{base_name}', starting from index {start_index}")
    return emails


def is_email_used(email: str) -> bool:
    used = email in load_used_gmails()
    if used:
        logger.debug(f"[EMAIL] {email} is already used")
    return used


def fetch_code_with_retry(
    email: str,
    max_wait: int = 40,
    poll_interval: float = 2.0,
) -> Optional[str]:
    logger.info(f"[CODE] Fetching verification code for {email} (max wait {max_wait}s)")
    deadline = time.time() + max_wait
    attempt = 1

    while time.time() < deadline:
        remaining = max(1, int(deadline - time.time()))
        attempt_timeout = max(3, min(10, remaining))

        logger.info(f"[CODE] Attempt {attempt} for {email} (timeout {attempt_timeout}s)")

        code = fetch_verification_code(
            email,
            timeout_sec=attempt_timeout,
            poll_interval=poll_interval,
        )

        if code:
            logger.success(f"Successfully fetched code {code} for {email}")  # using .success()
            return code

        logger.info(f"[CODE] Attempt {attempt} failed, next try in {poll_interval}s")
        attempt += 1
        time.sleep(poll_interval)

    logger.error(f"[CODE] ✗ Failed to fetch verification code for {email} after {max_wait}s")
    return None


def wait_for_verification_code(
    email: str,
    fetch_fn,
    timeout: int = 120,
    poll_interval: int = 5,
) -> Optional[str]:
    logger.info(f"[CODE] Waiting up to {timeout}s for code for {email}")
    start = time.time()
    attempt = 1

    while time.time() - start < timeout:
        logger.info(f"[CODE] Poll attempt {attempt} for {email}")
        code = fetch_fn(email)
        if code:
            logger.success(f"Code received for {email}: {code}")
            return code

        logger.info(f"[CODE] No code yet, next check in {poll_interval}s")
        attempt += 1
        time.sleep(poll_interval)

    logger.error(f"[CODE] ✗ Timed out after {timeout}s waiting for {email}")
    return None