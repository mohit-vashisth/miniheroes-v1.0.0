# src/email/pop_email.py
from typing import Optional
from src.email.email_state import email_queue, email_queue_lock

def pop_next_email() -> Optional[str]:
    with email_queue_lock:
        if email_queue:
            return email_queue.popleft()
        return None