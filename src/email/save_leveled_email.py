# src/email/save_leveled_email.py
import os
from src.config.config import LEVEL_SUCCESS_FILE
from src.utils.logging_setup import logger

def save_leveled_email(email: str):
    os.makedirs(os.path.dirname(LEVEL_SUCCESS_FILE), exist_ok=True)
    with open(LEVEL_SUCCESS_FILE, "a", encoding="utf-8") as f:
        f.write(email + "\n")
    logger.info(f"[LEVELED] {email} saved.")