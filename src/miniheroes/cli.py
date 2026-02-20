import time
import sys

# First import config to get LOG_FILE
from .config.config import LOG_FILE

# Setup logger immediately – before any other local imports
from .core.logger import setup_project_logger, log
setup_project_logger(log_file=LOG_FILE)
logger = log()  # now the logger is ready

# Now import the rest of the modules (they will use the initialized logger)
from .workflows.batch import (
    get_next_batch,
    get_statistics,
    process_batch,
)

from .workflows.list_emulators import (
    detect_running_emulator_indexes,
    close_emulators_in_parallel,
    delete_emulators_in_parallel
)
from .core.emulator_tracking import (
    get_used_emulator_indexes,
    mark_running_emulators_as_used
)
from .config.config import DELETE_USED_EMULATORS, IGNORED_EMULATORS

BANNER = """
    ██╗    ██╗███████╗██╗      ██████╗ ██████╗ ███╗   ███╗███████╗
    ██║    ██║██╔════╝██║     ██╔════╝██╔═══██╗████╗ ████║██╔════╝
    ██║ █╗ ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║█████╗
    ██║███╗██║██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║██╔══╝
    ╚███╔███╔╝███████╗███████╗╚██████╗╚██████╔╝██║ ╚═╝ ██║███████╗
    ╚══╝╚══╝ ╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝
    """

def print_banner():
    logger.info("="*80)
    logger.info("COMPLETE MULTI-EMULATOR AUTOMATION SCRIPT")
    logger.info("="*80)
    logger.info(BANNER)

def print_initial_stats():
    stats = get_statistics()
    logger.info("\n[INITIAL STATISTICS]")
    logger.info(f"Accounts Created: {stats.get('accounts', 0)}")
    logger.info(f"Emulators Used: {stats.get('emulators_used', 0)}")
    logger.info(f"Emulators Failed: {stats.get('emulators_failed', 0)}")
    logger.info(f"Batches Completed: {stats.get('batches_completed', 0)}")
    logger.info("-"*80)

def ensure_playwright_browsers():
    """Check if Playwright browsers are installed; if not, install them."""
    import subprocess
    from pathlib import Path

    browser_path = Path.home() / "AppData/Local/ms-playwright"
    if not browser_path.exists() or not any(browser_path.iterdir()):
        logger.info("[PLAYWRIGHT] Browsers not found. Installing now...")
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            logger.success("Playwright installation complete.")
        except subprocess.CalledProcessError:
            logger.error("Failed to install Playwright browsers. Please run manually:")
            logger.error("    playwright install chromium")
            sys.exit(1)

def main_loop():
    """Infinite batch processing loop."""
    batch_number = 1
    consecutive_failures = 0

    while True:
        try:
            # Get next batch of emulators
            batch_indexes, full_batch = get_next_batch()

            if not batch_indexes:
                logger.info("="*80)
                logger.info("ALL EMULATORS PROCESSED!")
                logger.info("="*80)
                break

            if not full_batch:
                logger.info(f"[PARTIAL BATCH] Only {len(batch_indexes)} emulators available")

            logger.info(f"{'='*60}")
            logger.info(f"PROCESSING BATCH {batch_number}")
            logger.info(f"Emulators: {batch_indexes}")
            logger.info(f"{'='*60}\n")

            # Process batch
            success = process_batch(batch_indexes, batch_number)

            if success:
                logger.success(f"BATCH {batch_number} COMPLETED SUCCESSFULLY")
                consecutive_failures = 0
            else:
                logger.fail(f"BATCH {batch_number} HAD ISSUES")
                consecutive_failures += 1

            # Show progress
            stats = get_statistics()
            logger.info("[PROGRESS UPDATE]")
            logger.info(f"Total Accounts: {stats.get('accounts', 0)}")
            if batch_number > 0:
                success_rate = (stats.get('accounts', 0) / (batch_number * 4 * 4)) * 100
                logger.info(f"Success Rate: {success_rate:.1f}%")

            # Handle consecutive failures
            if consecutive_failures >= 3:
                logger.warning("Too many consecutive failures! Taking 60s break...")
                time.sleep(60)
                consecutive_failures = 0

            # Wait before next batch
            wait_time = 20 if batch_number % 5 == 0 else 10
            logger.info(f"[WAITING] {wait_time} seconds before next batch...")
            time.sleep(wait_time)

            batch_number += 1

            # Safety limit (adjust as needed)
            if batch_number > 250:
                logger.info("[SAFETY LIMIT] Maximum batches reached")
                break

        except KeyboardInterrupt:
            logger.info("\n[STOPPED] User interrupted")
            break
        except Exception as e:
            logger.error(f"[CRITICAL ERROR] {e}")
            import traceback
            logger.debug(traceback.format_exc())
            time.sleep(30)

def final_cleanup():
    """Close any remaining emulators, delete used ones, and show final stats."""
    logger.info("="*80)
    logger.info("SCRIPT FINISHED")
    logger.info("="*80)

    stats = get_statistics()
    logger.info("[FINAL STATISTICS]")
    logger.info(f"Total Accounts Created: {stats.get('accounts', 0)}")
    logger.info(f"Total Emulators Used: {stats.get('emulators_used', 0)}")
    logger.info(f"Total Emulators Failed: {stats.get('emulators_failed', 0)}")

    # Cleanup: close running emulators
    logger.info("[CLEANUP] Closing any remaining emulators...")
    running = detect_running_emulator_indexes()
    if running:
        close_emulators_in_parallel(running)

    # Delete used emulators (if enabled)
    if DELETE_USED_EMULATORS:
        used_emus = get_used_emulator_indexes()
        # Filter out ignored emulators
        emus_to_delete = [idx for idx in used_emus if idx not in IGNORED_EMULATORS]
        ignored = [idx for idx in used_emus if idx in IGNORED_EMULATORS]

        if ignored:
            logger.info(f"[CLEANUP] Ignored {len(ignored)} emulators (in IGNORED_EMULATORS list): {ignored}")

        if emus_to_delete:
            logger.info(f"[CLEANUP] Deleting {len(emus_to_delete)} used emulators to free disk space...")
            delete_emulators_in_parallel(emus_to_delete)
        else:
            logger.info("[CLEANUP] No used emulators to delete (all ignored).")
    else:
        logger.info("[CLEANUP] Deletion of used emulators is disabled (DELETE_USED_EMULATORS=False).")

    logger.success("Script completed successfully!")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("="*80)

def main():
    """Main CLI entry point."""
    print_banner()
    ensure_playwright_browsers()
    print_initial_stats()
    mark_running_emulators_as_used()
    input("Press Enter to start automation (Ctrl+C to stop)...")
    try:
        main_loop()
    finally:
        final_cleanup()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"[FATAL ERROR] {e}")
        import traceback
        logger.debug(traceback.format_exc())
        input("\nPress Enter to exit...")