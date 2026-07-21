# src/mail_fetcher.py
import re
import html
import time
from typing import Optional

from playwright.sync_api import sync_playwright
from src.utils.logging_setup import logger

def fetch_verification_code(email: str, timeout: int = 45) -> Optional[str]:
    """
    Open maildrop.cc inbox and extract the latest verification code.
    Returns the code string, or None on timeout / error.
    """
    local = email.split("@")[0]
    inbox_url = f"https://maildrop.cc/inbox/?mailbox={local}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page()
        try:
            page.goto(inbox_url, timeout=15000)
            logger.info(f"[MAIL] Inbox opened for {email}")
            start = time.time()
            while time.time() - start < timeout:
                # Refresh
                try:
                    refresh_btn = page.locator('button:has-text("Refresh")')
                    if refresh_btn.count() > 0:
                        refresh_btn.click()
                except:
                    pass

                # Wait for a message
                try:
                    page.wait_for_selector("div.message", timeout=5000)
                    first_msg = page.locator("div.message").first
                    if first_msg.count() > 0:
                        first_msg.click()
                        time.sleep(1.5)

                        # iframe srcdoc
                        iframe = page.locator("iframe")
                        if iframe.count() > 0:
                            srcdoc = iframe.get_attribute("srcdoc")
                            if srcdoc:
                                unescaped = html.unescape(srcdoc)
                                m = re.search(r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4,6})", unescaped, re.IGNORECASE)
                                if m:
                                    code = m.group(1)
                                    logger.info(f"[MAIL] OTP received: {code}")
                                    browser.close()
                                    return code

                        # full page fallback
                        content = page.content()
                        m = re.search(r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4,6})", content, re.IGNORECASE)
                        if m:
                            code = m.group(1)
                            logger.info(f"[MAIL] OTP received: {code}")
                            browser.close()
                            return code
                except Exception:
                    pass
                time.sleep(3)
            logger.error("[MAIL] Timeout – code nahi mila")
            return None
        finally:
            browser.close()