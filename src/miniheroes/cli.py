import time
import logging
import sys

from .workflows.batch import (
    get_next_batch,
    get_statistics,
    process_batch,
)

from .workflows.list_emulators import (
    detect_running_emulator_indexes,
    close_emulators_in_parallel,
)

from .core.emulator_tracking import mark_running_emulators_as_used

from .config.config import LOG_FILE

logger = logging.getLogger(__name__)

BANNER = """
    Features Included:
    1 Fully Automatic MiniHeroes: Magic Throne (Account Creation tool)
       - Auto window hiding (off-screen positioning)
       - Detailed tap logging with coordinates
       - Parallel processing (4 emulators at once)
       - Error recovery and retry logic
       - Statistics tracking
       - Auto-closing emulators after use
       - Email verification code fetching
       - APK installation checking
       - Multi-method tap (dnconsole + adb fallback)
       - Optional pixel tap verification (default OFF)
    """

def print_banner():
    print("\n" + "="*80)
    print("COMPLETE MULTI-EMULATOR AUTOMATION SCRIPT")
    print("="*80)
    print(BANNER)

def print_initial_stats():
    stats = get_statistics()
    print("\n[INITIAL STATISTICS]")
    print(f"Accounts Created: {stats.get('accounts', 0)}")
    print(f"Emulators Used: {stats.get('emulators_used', 0)}")
    print(f"Emulators Failed: {stats.get('emulators_failed', 0)}")
    print(f"Batches Completed: {stats.get('batches_completed', 0)}")
    print("-"*80)

def ensure_playwright_browsers():
    """Check if Playwright browsers are installed; if not, install them."""
    import subprocess
    import sys
    from pathlib import Path

    browser_path = Path.home() / "AppData/Local/ms-playwright"
    if not browser_path.exists() or not any(browser_path.iterdir()):
        print("\n[PLAYWRIGHT] Browsers not found. Installing now...")
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            print("[PLAYWRIGHT] Installation complete.\n")
        except subprocess.CalledProcessError:
            print("\n[ERROR] Failed to install Playwright browsers. Please run manually:")
            print("    playwright install chromium")
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
                print("\n" + "="*80)
                print("ALL EMULATORS PROCESSED!")
                print("="*80)
                break

            if not full_batch:
                print(f"\n[PARTIAL BATCH] Only {len(batch_indexes)} emulators available")

            print(f"\n{'='*60}")
            print(f"PROCESSING BATCH {batch_number}")
            print(f"Emulators: {batch_indexes}")
            print(f"{'='*60}\n")

            # Process batch
            success = process_batch(batch_indexes, batch_number)

            if success:
                print(f"\n✓ BATCH {batch_number} COMPLETED SUCCESSFULLY")
                consecutive_failures = 0
            else:
                print(f"\n⚠ BATCH {batch_number} HAD ISSUES")
                consecutive_failures += 1

            # Show progress
            stats = get_statistics()
            print(f"\n[PROGRESS UPDATE]")
            print(f"Total Accounts: {stats.get('accounts', 0)}")
            if batch_number > 0:
                success_rate = (stats.get('accounts', 0) / (batch_number * 4 * 4)) * 100
                print(f"Success Rate: {success_rate:.1f}%")

            # Handle consecutive failures
            if consecutive_failures >= 3:
                print("\n[WARNING] Too many consecutive failures! Taking 60s break...")
                time.sleep(60)
                consecutive_failures = 0

            # Wait before next batch
            wait_time = 20 if batch_number % 5 == 0 else 10
            print(f"\n[WAITING] {wait_time} seconds before next batch...")
            time.sleep(wait_time)

            batch_number += 1

            # Safety limit (adjust as needed)
            if batch_number > 250:
                print("\n[SAFETY LIMIT] Maximum batches reached")
                break

        except KeyboardInterrupt:
            print("\n\n[STOPPED] User interrupted")
            break
        except Exception as e:
            print(f"\n[CRITICAL ERROR] {e}")
            import traceback
            traceback.print_exc()
            time.sleep(30)

def final_cleanup():
    """Close any remaining emulators and show final stats."""
    print("\n" + "="*80)
    print("SCRIPT FINISHED")
    print("="*80)

    stats = get_statistics()
    print("\n[FINAL STATISTICS]")
    print(f"Total Accounts Created: {stats.get('accounts', 0)}")
    print(f"Total Emulators Used: {stats.get('emulators_used', 0)}")
    print(f"Total Emulators Failed: {stats.get('emulators_failed', 0)}")

    # Cleanup
    print("\n[CLEANUP] Closing any remaining emulators...")
    running = detect_running_emulator_indexes()
    if running:
        close_emulators_in_parallel(running)

    print("\n✓ Script completed successfully!")
    print(f"Log file: {LOG_FILE}")
    print("="*80)

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
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")