# src/workflows/level35_workflow.py
import os
import time
from logging_setup import logger

import vision
from src.config.config import (
    LEVEL_35_YAML, CODES, FAST_RESUME_FILE
)
from src.adb.emu_launch import launch_emulator_by_index
from src.adb.emu_boot import wait_for_boot
from src.adb.emu_close import force_close_emulator
from src.adb.launch_game import launch_game
from src.email.pop_email import pop_next_email
from src.email.save_leveled_email import save_leveled_email
from src.yaml_exec.executor import execute_yaml_script

def run_level35_workflow(index: int) -> None:
    """Process all pending emails on a single emulator (level‑35)."""
    try:
        logger.info(f"\n{'='*30} Emulator {index} START {'='*30}")

        # Fast resume?
        if os.path.exists(FAST_RESUME_FILE):
            logger.info("⚡ FAST RESUME mode active.")
            logger.info(f"Assuming emulator {index} is already running and at home screen.")
            input("Press Enter when ready to continue (emulator must be at home screen)...")
        else:
            if not launch_emulator_by_index(index):
                return
            if not wait_for_boot(index):
                force_close_emulator(index)
                return
            if not launch_game(index):
                force_close_emulator(index)
                return
            logger.info(f"[{index}] Waiting for start screen...")
            try:
                vision.wait_for_image(index, "starting_page.png", retries=60, interval=1.0, confidence=0.7)
                logger.info(f"[{index}] Game fully loaded.")
            except TimeoutError:
                logger.error(f"[{index}] Game load timeout – proceeding anyway.")

        while True:
            email = pop_next_email()
            if email is None:
                logger.info(f"[{index}] No more emails, finishing.")
                break
            logger.info(f"[{index}] Processing: {email}")
            ok = execute_yaml_script(
                index, LEVEL_35_YAML, email,
                codes=CODES,
                wait_retries=30, wait_interval=0.9,
                tap_retries=30, tap_interval=0.9,
                enable_pause=True
            )
            if ok:
                save_leveled_email(email)
                logger.info(f"[{index}] {email} leveled successfully.")
            else:
                logger.error(f"[{index}] {email} failed leveling.")
            time.sleep(2)

        if not os.path.exists(FAST_RESUME_FILE):
            force_close_emulator(index)

    except Exception as e:
        logger.exception(f"[{index}] Fatal error: {e}")
        if not os.path.exists(FAST_RESUME_FILE):
            force_close_emulator(index)