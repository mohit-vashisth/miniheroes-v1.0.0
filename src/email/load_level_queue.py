# src/email/load_level_queue.py
import os
from src.config.config import EMAIL_SOURCE_FILE, LEVEL_SUCCESS_FILE
from src.utils.logging_setup import logger
from src.email.email_state import email_queue, email_queue_lock

def load_email_queue() -> bool:
    already_leveled = set()
    if os.path.exists(LEVEL_SUCCESS_FILE):
        with open(LEVEL_SUCCESS_FILE, "r", encoding="utf-8") as f:
            already_leveled = {line.strip() for line in f if line.strip()}
        logger.info(f"Found {len(already_leveled)} already‑leveled emails (will skip).")
    if not os.path.exists(EMAIL_SOURCE_FILE):
        logger.error(f"Email source file not found: {EMAIL_SOURCE_FILE}")
        return False
    with open(EMAIL_SOURCE_FILE, "r", encoding="utf-8") as f:
        all_emails = [line.strip() for line in f if line.strip()]
    new_emails = [e for e in all_emails if e not in already_leveled]
    with email_queue_lock:
        email_queue.extend(new_emails)
    logger.info(f"Loaded {len(new_emails)} new emails (skipped {len(all_emails)-len(new_emails)} already leveled).")
    return True