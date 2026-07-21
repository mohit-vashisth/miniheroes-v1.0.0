# src/workflows/register_workflow.py
import os
import time
import subprocess
from logging_setup import logger

import vision
from src.config.config import (
    LD_CONSOLE, GAME_PACKAGE, GMAIL_PREFIX, IGNORED_EMULATOR_INDEXES, WORKERS, REGISTER_YAML
)
from src.adb.emu_launch import launch_emulator_by_index
from src.adb.emu_boot import wait_for_boot
from src.adb.emu_close import force_close_emulator
from src.adb.emu_list import get_all_emulator_indices
from src.adb.launch_game import launch_game
from src.apk.install_and_verify_apks import install_and_verify_apks
from src.apk.clear_game_data import clear_game_data
from src.email.generate_email import get_next_email
from src.file_utils.load_used_emulators import load_used_emulators
from src.file_utils.save_used_emulator import save_used_emulator
from src.file_utils.load_failed_emulators import load_failed_emulators
from src.file_utils.save_failed_emulator import save_failed_emulator
from src.yaml_exec.executor import execute_yaml_script

def run_register_workflow(index: int) -> bool:
    """Run 4 account creations on the given emulator. Returns True if at least 3 succeeded."""
    emulator_launched = False
    try:
        logger.info(f"\n{'='*30} Emulator {index} START {'='*30}")
        if not launch_emulator_by_index(index):
            return False
        emulator_launched = True
        if not wait_for_boot(index):
            return False
        logger.info(f"[{index}] Ready for install.")
        if not install_and_verify_apks(index):
            return False

        success_runs = 0
        for run_num in range(1, 5):
            logger.info(f"\n[{index}] --- Run {run_num}/4 ---")
            subprocess.run([LD_CONSOLE, "adb", "--index", str(index), "--command", f"shell am force-stop {GAME_PACKAGE}"],
                           capture_output=True, timeout=10)
            time.sleep(1)
            clear_game_data(index)
            if not launch_game(index):
                logger.error(f"[{index}] Game launch failed for run {run_num}.")
                if run_num == 1:
                    save_failed_emulator(index)
                return False
            if run_num == 1:
                save_used_emulator(index)
            logger.info(f"[{index}] Waiting for start screen...")
            try:
                vision.wait_for_image(index, "starting_page.png", retries=60, interval=1.0, confidence=0.7)
                logger.info(f"[{index}] Game fully loaded.")
            except TimeoutError:
                logger.error(f"[{index}] Game load timeout – proceeding anyway.")
            email = get_next_email(GMAIL_PREFIX)
            logger.info(f"[{index}] Using email: {email}")
            ok = execute_yaml_script(index, REGISTER_YAML, email)
            if ok:
                logger.info(f"[{index}] Run {run_num} successful!")
                with open("data/used_gmails.txt", "a") as f:
                    f.write(email + "\n")
                success_runs += 1
            else:
                logger.error(f"[{index}] Run {run_num} failed.")
        logger.info(f"[{index}] Finished: {success_runs}/4 successful")
        return success_runs >= 3
    except Exception as e:
        logger.exception(f"[{index}] Unexpected error: {e}")
        return False
    finally:
        if emulator_launched:
            try:
                force_close_emulator(index)
            except Exception:
                pass