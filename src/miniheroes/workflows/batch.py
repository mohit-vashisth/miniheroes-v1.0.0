from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

from ..auth.email_utils import generate_fresh_emails
from ..config.config import BASE_NAME, BATCH_SIZE, MAX_EMULATORS, USED_ACCOUNTS_FILE
from ..core.emulator_tracking import (
    get_failed_emulator_indexes,
    get_used_emulator_indexes,
    save_failed_emulator_index,
    save_used_emulator_index,
)
from ..core.logger import log
from .emulator_cycle import process_single_emulator
from .list_emulators import close_emulators_in_parallel, start_and_wait_for_emulators
from .split_apk_installer import install_apks_in_parallel


logger = log()


def get_next_batch() -> Tuple[List[int], bool]:
    used_indexes = get_used_emulator_indexes()
    failed_indexes = get_failed_emulator_indexes()

    logger.debug(f"[BATCH] Used indexes: {sorted(used_indexes)}")
    logger.debug(f"[BATCH] Failed indexes: {sorted(failed_indexes)}")

    batch: List[int] = []
    for idx in range(MAX_EMULATORS):
        if idx in used_indexes or idx in failed_indexes:
            continue
        batch.append(idx)
        if len(batch) == BATCH_SIZE:
            break

    if batch:
        logger.info(f"[BATCH] Next batch: {batch} (full={len(batch)==BATCH_SIZE})")
    else:
        logger.warning("[BATCH] No available emulators found")

    return batch, len(batch) == BATCH_SIZE


def get_statistics() -> Dict[str, int]:
    accounts = 0
    used_accounts_path = Path(USED_ACCOUNTS_FILE)
    if used_accounts_path.exists():
        with used_accounts_path.open("r", encoding="utf-8") as handle:
            accounts = sum(1 for line in handle if line.strip())

    used_emulators = len(get_used_emulator_indexes())
    failed_emulators = len(get_failed_emulator_indexes())
    completed_batches = accounts // (BATCH_SIZE * 4)

    stats = {
        "accounts": accounts,
        "emulators_used": used_emulators,
        "emulators_failed": failed_emulators,
        "batches_completed": completed_batches,
    }

    logger.debug(f"[STATS] Current statistics: {stats}")
    return stats


def process_batch(batch_indexes: List[int], batch_number: int) -> bool:
    logger.section(f"BATCH {batch_number}")
    logger.info(f"Processing emulators: {batch_indexes}")

    if not batch_indexes:
        logger.warning("[BATCH] No indexes provided")
        return False

    try:
        # STEP 1: Start emulators
        logger.step(1, "Starting emulators")
        started_map = start_and_wait_for_emulators(batch_indexes)
        started_indexes = [idx for idx, started in started_map.items() if started]

        if not started_indexes:
            logger.error("[BATCH] No emulators started successfully")
            return False

        logger.info(f"[BATCH] Started {len(started_indexes)}/{len(batch_indexes)} emulators: {started_indexes}")

        # STEP 2: Install APKs
        logger.step(2, "Installing APKs")
        install_ok_indexes = install_apks_in_parallel(started_indexes)

        if not install_ok_indexes:
            logger.error("[BATCH] APK installation failed for all started emulators")
            return False

        logger.info(f"[BATCH] APK install successful on {len(install_ok_indexes)} emulators: {install_ok_indexes}")

        # STEP 3: Generate emails
        logger.step(3, "Generating emails")
        total_emails = len(install_ok_indexes) * 4
        email_pool = generate_fresh_emails(BASE_NAME, total_emails)
        email_groups = [email_pool[i : i + 4] for i in range(0, len(email_pool), 4)]
        logger.info(f"[BATCH] Generated {total_emails} emails for {len(install_ok_indexes)} emulators")

        # STEP 4: Process emulators in parallel
        logger.step(4, "Running emulator cycles in parallel")
        success_count = 0
        max_workers = max(1, min(len(install_ok_indexes), 8))
        logger.info(f"[BATCH] Using {max_workers} parallel workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for idx, emulator_index in enumerate(install_ok_indexes):
                emails_for_emulator = email_groups[idx] if idx < len(email_groups) else []
                future = executor.submit(process_single_emulator, emulator_index, emails_for_emulator)
                future_map[future] = emulator_index
                logger.debug(f"[BATCH] Submitted emulator {emulator_index} for processing")

            completed = 0
            for future in as_completed(future_map):
                completed += 1
                emulator_index = future_map[future]
                logger.progress(completed, len(future_map), f"Emulator {emulator_index}")

                try:
                    emulator_success = bool(future.result())
                except Exception as exc:
                    logger.error(f"[BATCH] Emulator {emulator_index} crashed: {exc}")
                    emulator_success = False

                if emulator_success:
                    save_used_emulator_index(emulator_index)
                    success_count += 1
                    logger.success(f"Emulator {emulator_index} completed successfully")
                else:
                    save_failed_emulator_index(emulator_index)
                    logger.fail(f"Emulator {emulator_index} failed")

        # Mark any started emulators that didn't get installed as failed
        for emulator_index in started_indexes:
            if emulator_index not in install_ok_indexes:
                save_failed_emulator_index(emulator_index)
                logger.warning(f"[BATCH] Emulator {emulator_index} started but install failed, marked as failed")

        # STEP 5: Close emulators
        logger.step(5, "Closing emulators")
        close_emulators_in_parallel(batch_indexes)

        logger.info(f"[BATCH] Completed with {success_count}/{len(install_ok_indexes)} successful emulators")

        if success_count > 0:
            logger.success(f"Batch {batch_number} completed with {success_count} successes")
        else:
            logger.fail(f"Batch {batch_number} completed with 0 successes")

        return success_count > 0

    except Exception as exc:
        logger.error(f"[BATCH] Fatal error in batch {batch_number}: {exc}")
        import traceback
        logger.debug(traceback.format_exc())

        # Try to close emulators even on error
        try:
            logger.info("[BATCH] Attempting to close emulators after error")
            close_emulators_in_parallel(batch_indexes)
        except Exception as close_error:
            logger.error(f"[BATCH] Error while closing emulators: {close_error}")

        return False