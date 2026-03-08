import html
import re
import time
from typing import List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from ..core.logger import log

logger = log()


def generate_mailboxes(base_name: str, count: int, start_index: int = 1) -> List[str]:
    emails = [f"{base_name}{i}@maildrop.cc" for i in range(start_index, start_index + count)]
    logger.info(f"[MAILBOX] Generated {count} mailboxes from {emails[0]} to {emails[-1]}")
    return emails


def fetch_verification_code(
    mailbox: str,
    timeout_sec: int = 30,
    poll_interval: float = 1.0,
    debug: bool = False,
    max_hard_reloads: int = 3,
) -> Optional[str]:
    local = mailbox.split("@")[0]
    inbox_url = f"https://maildrop.cc/inbox/?mailbox={local}"
    start_ts = time.time()
    hard_reload_count = 0

    logger.info(f"[CODE] Fetching verification code for {mailbox} (timeout {timeout_sec}s)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Initial navigation
            logger.debug(f"[CODE] Navigating to inbox: {inbox_url}")
            try:
                page.goto(inbox_url, timeout=10000)
                logger.debug("[CODE] Page loaded successfully")
            except PlaywrightTimeoutError:
                logger.warning("[CODE] Initial navigation timed out, retrying once...")
                try:
                    page.goto(inbox_url, timeout=10000)
                    logger.debug("[CODE] Page loaded on retry")
                except PlaywrightTimeoutError:
                    logger.error("[CODE] Unable to load inbox page after retry")
                    return None   # ← return None instead of raising

            while True:
                elapsed = time.time() - start_ts
                if elapsed > timeout_sec:
                    logger.error(f"[CODE] Timeout after {timeout_sec}s, no message found")
                    return None   # ← return None on timeout

                # Wait for a message element
                try:
                    page.wait_for_selector("div.message", timeout=int(poll_interval * 1000))
                    logger.debug("[CODE] Message element appeared")
                except PlaywrightTimeoutError:
                    # No message yet; refresh or reload
                    logger.debug(f"[CODE] No message yet after {elapsed:.1f}s, refreshing...")
                    try:
                        refresh_btn = page.query_selector('button:has-text("Refresh")')
                        if refresh_btn:
                            refresh_btn.click()
                            logger.debug("[CODE] Clicked Refresh button")
                            time.sleep(0.25)
                        else:
                            if hard_reload_count < max_hard_reloads:
                                hard_reload_count += 1
                                logger.debug(f"[CODE] Performing page.reload() ({hard_reload_count}/{max_hard_reloads})")
                                page.reload(timeout=15000)
                            else:
                                logger.debug("[CODE] Waiting without reload")
                                time.sleep(max(poll_interval, 1.0))
                    except Exception as exc:
                        logger.debug(f"[CODE] Refresh attempt failed: {exc}")
                        time.sleep(poll_interval)
                    continue

                # Click the message
                msg_el = page.query_selector("div.message")
                if not msg_el:
                    logger.debug("[CODE] Message element disappeared, retrying")
                    time.sleep(0.2)
                    continue

                try:
                    msg_el.click()
                    logger.debug("[CODE] Clicked message")
                except Exception:
                    page.evaluate("(el) => el.click()", msg_el)
                    logger.debug("[CODE] Clicked message via JS")

                # Wait for iframe (the email content)
                try:
                    page.wait_for_selector("iframe", timeout=5000)
                    logger.debug("[CODE] iframe appeared")
                except PlaywrightTimeoutError:
                    # No iframe, try to extract from page text directly
                    logger.debug("[CODE] No iframe, attempting direct text extraction")
                    try:
                        body_text = None
                        if page.query_selector("div.mb-16"):
                            body_text = page.inner_text("div.mb-16")
                        else:
                            body_text = page.content()
                        match = re.search(
                            r"verification code[:\s]*([A-Za-z0-9]{4})",
                            body_text,
                            re.IGNORECASE | re.DOTALL,
                        )
                        if match:
                            code = match.group(1)
                            logger.success(f"Found code {code} in page text")
                            return code
                    except Exception as exc:
                        logger.debug(f"[CODE] Fallback extraction failed: {exc}")
                    time.sleep(0.5)
                    continue

                # Iframe present, try srcdoc
                iframe_el = page.query_selector("iframe")
                if not iframe_el:
                    logger.debug("[CODE] iframe disappeared")
                    time.sleep(0.2)
                    continue

                srcdoc = iframe_el.get_attribute("srcdoc")
                if srcdoc:
                    unescaped = html.unescape(srcdoc)
                    logger.debug("[CODE] Extracting from iframe srcdoc")
                    match = re.search(
                        r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4})\s*(?:</strong>)?",
                        unescaped,
                        re.IGNORECASE | re.DOTALL,
                    )
                    if match:
                        code = match.group(1)
                        logger.success(f"Found code {code} in iframe srcdoc")
                        return code

                # Try to access iframe content
                try:
                    frame = iframe_el.content_frame()
                    if frame:
                        try:
                            email_text = frame.inner_text("body")
                        except Exception:
                            email_text = frame.content() or ""
                        logger.debug("[CODE] Extracting from iframe body")
                        match = re.search(
                            r"verification code[:\s]*([A-Za-z0-9]{4})",
                            email_text,
                            re.IGNORECASE | re.DOTALL,
                        )
                        if match:
                            code = match.group(1)
                            logger.success(f"Found code {code} in iframe body")
                            return code
                except Exception as exc:
                    logger.debug(f"[CODE] content_frame extraction failed: {exc}")

                # Final fallback: entire page HTML
                page_html = page.content()
                logger.debug("[CODE] Fallback: searching full page HTML")
                match = re.search(
                    r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4})",
                    page_html,
                    re.IGNORECASE | re.DOTALL,
                )
                if match:
                    code = match.group(1)
                    logger.success(f"Found code {code} in page HTML")
                    return code

                logger.debug("[CODE] No code found yet, retrying")
                time.sleep(0.5)

        finally:
            try:
                browser.close()
                logger.debug("[CODE] Browser closed")
            except Exception:
                pass