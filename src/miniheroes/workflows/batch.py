# batch.py
from __future__ import annotations

import logging
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
from .emulator_cycle import process_single_emulator
from .list_emulators import close_emulators_in_parallel, start_and_wait_for_emulators
from .split_apk_installer import install_apks_in_parallel


logger = logging.getLogger(__name__)


def get_next_batch() -> Tuple[List[int], bool]:
    used_indexes = get_used_emulator_indexes()
    failed_indexes = get_failed_emulator_indexes()

    batch: List[int] = []
    for idx in range(MAX_EMULATORS):
        if idx in used_indexes or idx in failed_indexes:
            continue
        batch.append(idx)
        if len(batch) == BATCH_SIZE:
            break

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

    return {
        "accounts": accounts,
        "emulators_used": used_emulators,
        "emulators_failed": failed_emulators,
        "batches_completed": completed_batches,
    }


def process_batch(batch_indexes: List[int], batch_number: int) -> bool:
    logger.info("========== BATCH %s ==========", batch_number)
    logger.info("[BATCH] indexes=%s", batch_indexes)

    if not batch_indexes:
        logger.warning("[BATCH] no indexes provided")
        return False

    try:
        logger.info("[STEP 1] starting emulators")
        started_map = start_and_wait_for_emulators(batch_indexes)
        started_indexes = [idx for idx, started in started_map.items() if started]
        if not started_indexes:
            logger.error("[BATCH] no emulators started")
            return False

        logger.info("[STEP 2] installing split APKs")
        install_ok_indexes = install_apks_in_parallel(started_indexes)
        if not install_ok_indexes:
            logger.error("[BATCH] APK install failed for all started emulators")
            return False

        logger.info("[STEP 3] generating emails")
        total_emails = len(install_ok_indexes) * 4
        email_pool = generate_fresh_emails(BASE_NAME, total_emails)
        email_groups = [email_pool[i : i + 4] for i in range(0, len(email_pool), 4)]

        logger.info("[STEP 4] running emulator cycles in parallel")
        success_count = 0
        max_workers = max(1, min(len(install_ok_indexes), 8))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for idx, emulator_index in enumerate(install_ok_indexes):
                emails_for_emulator = email_groups[idx] if idx < len(email_groups) else []
                future = executor.submit(process_single_emulator, emulator_index, emails_for_emulator)
                future_map[future] = emulator_index

            for future in as_completed(future_map):
                emulator_index = future_map[future]
                try:
                    emulator_success = bool(future.result())
                except Exception as exc:
                    logger.error("[BATCH] emulator %s crashed: %s", emulator_index, exc)
                    emulator_success = False

                if emulator_success:
                    save_used_emulator_index(emulator_index)
                    success_count += 1
                    logger.info("[BATCH] emulator %s success", emulator_index)
                else:
                    save_failed_emulator_index(emulator_index)
                    logger.warning("[BATCH] emulator %s failed", emulator_index)

        for emulator_index in started_indexes:
            if emulator_index not in install_ok_indexes:
                save_failed_emulator_index(emulator_index)

        logger.info("[STEP 5] closing emulators")
        close_emulators_in_parallel(batch_indexes)

        logger.info("[BATCH] completed with %s successful emulators", success_count)
        return success_count > 0
    except Exception as exc:
        logger.error("[BATCH] fatal error: %s", exc)
        try:
            close_emulators_in_parallel(batch_indexes)
        except Exception:
            pass
        return False

