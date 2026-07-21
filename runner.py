# runner.py
"""Unified runner – choose which workflow to start."""

import concurrent.futures
import sys
from src.utils.logging_setup import logger

# Import everything needed for both workflows
from src.config.config import (
    MY_EMULATORS,
    IGNORED_EMULATOR_INDEXES,
    WORKERS,
)
from src.adb.emu_list import get_all_emulator_indices
from src.file_utils.load_used_emulators import load_used_emulators
from src.file_utils.load_failed_emulators import load_failed_emulators
from src.file_utils.save_failed_emulator import save_failed_emulator
from src.email.load_level_queue import load_email_queue


def run_register():
    """Registration workflow."""
    from src.workflows.register_workflow import run_register_workflow

    all_idx = get_all_emulator_indices()
    if not all_idx:
        logger.error("No emulators found via list2. Exiting.")
        return

    used = load_used_emulators()
    failed = load_failed_emulators()
    ignored = set(IGNORED_EMULATOR_INDEXES)
    remaining = [idx for idx in all_idx if idx not in used and idx not in failed and idx not in ignored]
    if not remaining:
        logger.error("All emulators processed or ignored.")
        return

    logger.info(f"Total remaining emulators: {len(remaining)}")
    input("Press Enter to start registration...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        future_to_idx = {executor.submit(run_register_workflow, idx): idx for idx in remaining}
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                success = future.result()
            except Exception as e:
                logger.error(f"[{idx}] Exception: {e}")
                success = False
            if not success:
                if idx not in load_used_emulators():
                    save_failed_emulator(idx)
                    logger.error(f"[{idx}] Marked as failed.")


def run_level35():
    """Level‑35 workflow."""
    from src.workflows.level35_workflow import run_level35_workflow

    if not load_email_queue():
        return

    logger.info(f"Using emulators: {MY_EMULATORS}")
    input("Press Enter to start level‑35 automation...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(run_level35_workflow, idx) for idx in MY_EMULATORS]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Unhandled exception in task: {e}")


def main():
    print("=" * 60)
    print("MINIHEROES AUTOMATION")
    print("=" * 60)
    print("1. Register new accounts")
    print("2. Level‑35 (login + level up)")
    print("=" * 60)

    try:
        choice = input("Choose an option (1/2): ").strip()
        if choice == "1":
            logger.info("Starting REGISTRATION workflow...")
            run_register()
        elif choice == "2":
            logger.info("Starting LEVEL‑35 workflow...")
            run_level35()
        else:
            print("Invalid choice. Exiting.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted by user.")
    finally:
        logger.info("All tasks completed. Exiting.")


if __name__ == "__main__":
    main()