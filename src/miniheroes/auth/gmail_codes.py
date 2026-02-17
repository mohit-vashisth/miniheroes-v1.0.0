# gmail_codes.py
import html
import re
import time
from typing import List, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def generate_mailboxes(base_name: str, count: int, start_index: int = 1) -> List[str]:
    return [f"{base_name}{i}@maildrop.cc" for i in range(start_index, start_index + count)]


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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            try:
                page.goto(inbox_url, timeout=10000)
            except PlaywrightTimeoutError:
                if debug:
                    print("Initial page.goto timed out; retrying once...")
                try:
                    page.goto(inbox_url, timeout=10000)
                except PlaywrightTimeoutError:
                    raise Exception("Unable to load inbox page (initial navigation timed out).")

            while True:
                elapsed = time.time() - start_ts
                if elapsed > timeout_sec:
                    raise Exception(f"No message/code found within {timeout_sec} seconds for {local}")

                try:
                    page.wait_for_selector("div.message", timeout=int(poll_interval * 1000))
                except PlaywrightTimeoutError:
                    if debug:
                        print(f"[{int(elapsed)}s] no message visible; attempting client-side refresh or light reload")

                    try:
                        refresh_btn = page.query_selector('button:has-text("Refresh")')
                        if refresh_btn:
                            refresh_btn.click()
                            time.sleep(0.25)
                        else:
                            if hard_reload_count < max_hard_reloads:
                                hard_reload_count += 1
                                if debug:
                                    print(f"Performing light page.reload() ({hard_reload_count}/{max_hard_reloads})")
                                page.reload(timeout=15000)
                            else:
                                time.sleep(max(poll_interval, 1.0))
                    except Exception as exc:
                        if debug:
                            print("Refresh attempt failed:", exc)
                        time.sleep(poll_interval)
                    continue

                msg_el = page.query_selector("div.message")
                if not msg_el:
                    time.sleep(0.2)
                    continue

                try:
                    msg_el.click()
                except Exception:
                    page.evaluate("(el) => el.click()", msg_el)

                try:
                    page.wait_for_selector("iframe", timeout=5000)
                except PlaywrightTimeoutError:
                    try:
                        body_text = None
                        if page.query_selector("div.mb-16"):
                            body_text = page.inner_text("div.mb-16")
                        else:
                            body_text = page.content()
                        if debug:
                            print("No iframe; fallback body/text preview:")
                            print(body_text[:2000])
                        match = re.search(
                            r"verification code[:\s]*([A-Za-z0-9]{4})",
                            body_text,
                            re.IGNORECASE | re.DOTALL,
                        )
                        if match:
                            return match.group(1)
                    except Exception as exc:
                        if debug:
                            print("Fallback extraction failed:", exc)
                    time.sleep(0.5)
                    continue

                iframe_el = page.query_selector("iframe")
                if not iframe_el:
                    time.sleep(0.2)
                    continue

                srcdoc = iframe_el.get_attribute("srcdoc")
                if srcdoc:
                    unescaped = html.unescape(srcdoc)
                    if debug:
                        print("Found iframe srcdoc (preview):")
                        print(unescaped[:1000])
                    match = re.search(
                        r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4})\s*(?:</strong>)?",
                        unescaped,
                        re.IGNORECASE | re.DOTALL,
                    )
                    if match:
                        return match.group(1)

                try:
                    frame = iframe_el.content_frame()
                    if frame:
                        try:
                            email_text = frame.inner_text("body")
                        except Exception:
                            email_text = frame.content() or ""
                        if debug:
                            print("Frame body (preview):")
                            print(email_text[:1000])
                        match = re.search(
                            r"verification code[:\s]*([A-Za-z0-9]{4})",
                            email_text,
                            re.IGNORECASE | re.DOTALL,
                        )
                        if match:
                            return match.group(1)
                except Exception as exc:
                    if debug:
                        print("content_frame fallback failed:", exc)

                page_html = page.content()
                if debug:
                    print("Final fallback page HTML preview (truncated):")
                    print(page_html[:1000])
                match = re.search(
                    r"verification code[:\s]*?(?:<strong>)?\s*([A-Za-z0-9]{4})",
                    page_html,
                    re.IGNORECASE | re.DOTALL,
                )
                if match:
                    return match.group(1)

                time.sleep(0.5)
        finally:
            try:
                browser.close()
            except Exception:
                pass

