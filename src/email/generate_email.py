# src/email/generate_email.py
import os
import json
import threading
from src.config.config import GMAIL_PREFIX, EMAIL_COUNTER_FILE
from src.utils.logging_setup import logger

_email_lock = threading.Lock()

def get_next_email(prefix: str = GMAIL_PREFIX) -> str:
    with _email_lock:
        os.makedirs(os.path.dirname(EMAIL_COUNTER_FILE), exist_ok=True)
        if os.path.exists(EMAIL_COUNTER_FILE):
            with open(EMAIL_COUNTER_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"next": 1}
        next_id = data["next"]
        email = f"{prefix}{next_id}@maildrop.cc"
        data["next"] = next_id + 1
        with open(EMAIL_COUNTER_FILE, "w") as f:
            json.dump(data, f)
    logger.info(f"[EMAIL] Generated: {email}")
    return email