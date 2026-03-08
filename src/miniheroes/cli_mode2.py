import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config.config import LOG_FILE
from .core.logger import setup_project_logger, log

setup_project_logger(log_file=LOG_FILE)
logger = log()

from .auth.used_accounts_track import load_used_gmails
from .auth.level35_track import load_level35_accounts
from .workflows.mode2_automation import process_one_account
from .workflows.list_emulators import (
    start_and_wait_for_emulators,
    detect_running_emulator_indexes,
)

# The four fixed emulators that are already running (by port)
# port 5560 -> index 3, 5562 -> 4, 5564 -> 5, 5566 -> 6
FIXED_EMULATOR_INDEXES = [3, 4, 5, 6]
EMULATOR_DEVICES = [f"emulator-{5554 + i*2}" for i in FIXED_EMULATOR_INDEXES]  # generates emulator-5560 etc.


def ensure_emulators_running():
    """Check if the fixed emulators are running; start any that are not in parallel."""
    running_indexes = set(detect_running_emulator_indexes())
    logger.info(f"[MODE2] Currently running emulator indexes: {sorted(running_indexes)}")

    missing = [idx for idx in FIXED_EMULATOR_INDEXES if idx not in running_indexes]
    if missing:
        logger.info(f"[MODE2] Starting missing emulators in parallel: {missing}")
        results, newly = start_and_wait_for_emulators(missing)
        # Check each missing index succeeded
        failed = [idx for idx in missing if not results.get(idx, False)]
        if failed:
            logger.error(f"[MODE2] Failed to start emulators: {failed}")
            sys.exit(1)
        logger.success(f"[MODE2] All missing emulators started successfully.")
    else:
        logger.info("[MODE2] All fixed emulators are already running.")


def get_pending_accounts():
    """Return all used accounts that are not yet level‑35."""
    all_used = load_used_gmails()
    level35 = load_level35_accounts()
    pending = [email for email in all_used if email not in level35]
    logger.info(
        f"[MODE2] Pending accounts: {len(pending)} "
        f"(total used: {len(all_used)}, level35: {len(level35)})"
    )
    return pending


def main():
    print("=" * 80)
    print("MODE 2 – Level 35 Automation (Fixed Emulators)")
    print("=" * 80)

    # Ensure all required emulators are running
    ensure_emulators_running()

    pending = get_pending_accounts()
    if not pending:
        logger.info("[MODE2] No pending accounts to process.")
        return

    logger.info(f"[MODE2] Will process {len(pending)} accounts on {len(EMULATOR_DEVICES)} fixed emulators")

    batch_size = len(EMULATOR_DEVICES)
    total = len(pending)
    completed = 0

    # Process in batches of 4
    for i in range(0, total, batch_size):
        batch = pending[i:i + batch_size]
        logger.section(f"Batch {i // batch_size + 1}: {len(batch)} accounts")

        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            future_to_email = {}
            for j, email in enumerate(batch):
                dev = EMULATOR_DEVICES[j % batch_size]
                future = executor.submit(process_one_account, dev, email)
                future_to_email[future] = email

            for future in as_completed(future_to_email):
                email = future_to_email[future]
                try:
                    success = future.result()
                    if success:
                        completed += 1
                        logger.success(f"Account {email} done ({completed}/{total})")
                    else:
                        logger.error(f"Account {email} failed")
                except Exception as e:
                    logger.error(f"Account {email} threw exception: {e}")

        # Short pause between batches
        time.sleep(5)

    logger.success(f"[MODE2] All done! {completed}/{total} accounts reached level 35.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("[MODE2] Interrupted by user")
    except Exception as e:
        logger.error(f"[MODE2] Fatal error: {e}")
        import traceback
        logger.debug(traceback.format_exc())