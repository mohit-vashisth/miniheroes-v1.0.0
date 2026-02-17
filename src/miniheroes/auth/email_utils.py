# email_utils.py
from __future__ import annotations

import time
from typing import List, Optional


from .gmail_codes import fetch_verification_code, generate_mailboxes
from .used_accounts_track import get_next_mailbox_index, load_used_gmails


def generate_fresh_emails(base_name: str, count: int, domain: str = "maildrop.cc") -> List[str]:
    start_index = get_next_mailbox_index(base_name, domain=domain, min_index=1)
    return generate_mailboxes(base_name, count, start_index=start_index)


def is_email_used(email: str) -> bool:
    return email in load_used_gmails()


def fetch_code_with_retry(
    email: str,
    max_wait: int = 40,
    poll_interval: float = 2.0,
) -> Optional[str]:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        remaining = max(1, int(deadline - time.time()))
        attempt_timeout = max(3, min(10, remaining))
        code = fetch_verification_code(
            email,
            timeout_sec=attempt_timeout,
            poll_interval=poll_interval,
        )
        if code:
            return code
        time.sleep(poll_interval)
    return None

def wait_for_verification_code(
    email: str,
    fetch_fn,
    timeout: int = 120,
    poll_interval: int = 5,
) -> Optional[str]:
    start = time.time()

    while time.time() - start < timeout:
        code = fetch_fn(email)
        if code:
            return code

        time.sleep(poll_interval)

    return None