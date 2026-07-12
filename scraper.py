#!/usr/bin/env python3
"""
Notice Scraper for CUExam.net and Scottish Church College.
Scrapes exam & college notices, stores seen IDs in seen_notices.json,
and sends notifications for new notices via WhatsApp Cloud API.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("NoticeScraper")

DEFAULT_TIMEOUT = 15  # seconds
SEEN_FILE = "seen_notices.json"


class TimeoutHTTPAdapter(HTTPAdapter):
    """Custom HTTPAdapter that enforces a default timeout on all requests."""

    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs.pop("timeout")
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


def get_http_session(retries=3, backoff_factor=1.0) -> requests.Session:
    """Create a robust HTTP session with retries, exponential backoff, and timeouts."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 NoticeScraperBot/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })

    retry_strategy = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST"],
    )

    adapter = TimeoutHTTPAdapter(max_retries=retry_strategy, timeout=DEFAULT_TIMEOUT)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def make_notice_id(source_prefix: str, url: str) -> str:
    """Generate a stable unique ID for a notice based on source prefix and URL."""
    url_hash = hashlib.md5(url.strip().encode("utf-8")).hexdigest()
    return f"{source_prefix}:{url_hash}"


def scrape_cuexam(session: requests.Session) -> list[dict]:
    """Scrape official notices from CUExam.net (exam-notice.php)."""
    base_url = "https://cuexam.net/"
    target_url = "https://cuexam.net/exam-notice.php"
    logger.info(f"Scraping CUExam.net notices from {target_url}...")

    notices = []
    try:
        response = session.get(target_url)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch CUExam.net notices: {e}")
        return notices

    soup = BeautifulSoup(response.text, "html.parser")
    # Rows inside the notice table
    rows = soup.find_all("tr")
    for row in rows:
        link_tag = row.find("a")
        if not link_tag or not link_tag.get("href"):
            continue

        href = link_tag.get("href").strip()
        # Filter for notice links
        if not ("notices/" in href or href.endswith(".pdf")):
            continue

        absolute_url = urljoin(base_url, href)
        title = link_tag.get_text(strip=True)
        if not title:
            continue

        # Try to find date in the row cells
        date_text = "N/A"
        tds = row.find_all("td")
        if len(tds) >= 3:
            date_text = tds[-1].get_text(strip=True)

        notice_id = make_notice_id("cuexam", absolute_url)
        notices.append({
            "id": notice_id,
            "source": "CUExam.net",
            "title": title,
            "date": date_text,
            "url": absolute_url,
        })

    logger.info(f"Found {len(notices)} notices from CUExam.net.")
    return notices


def scrape_scottish_church(session: requests.Session) -> list[dict]:
    """Scrape official notices from Scottish Church College (notice-board.php)."""
    base_url = "https://www.scottishchurch.ac.in/"
    target_url = "https://www.scottishchurch.ac.in/notice-board.php"
    logger.info(f"Scraping Scottish Church College notices from {target_url}...")

    notices = []
    try:
        response = session.get(target_url)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch Scottish Church College notices: {e}")
        return notices

    soup = BeautifulSoup(response.text, "html.parser")
    # Notices are typically in list items <li> with links to pdfs/docs
    list_items = soup.find_all("li")
    for li in list_items:
        link_tag = li.find("a")
        if not link_tag or not link_tag.get("href"):
            continue

        href = link_tag.get("href").strip()
        # Filter for relevant documents/uploads
        if not any(sub in href for sub in ["noticeUpload/", "docs/", ".pdf", "notice"]):
            continue

        absolute_url = urljoin(base_url, href)

        # Extract date span if present
        date_span = link_tag.find("span", class_="notice_date") or li.find("span", class_="notice_date")
        date_text = date_span.get_text(strip=True) if date_span else "N/A"

        # Remove image tags / date span from text to get clean title
        for img in link_tag.find_all("img"):
            img.decompose()
        if date_span:
            date_span.decompose()

        raw_text = link_tag.get_text(separator=" ", strip=True)
        # Clean leading hyphens or dates leftover
        title = raw_text.lstrip("-: ").strip()
        if not title:
            title = os.path.basename(href)

        notice_id = make_notice_id("scc", absolute_url)
        notices.append({
            "id": notice_id,
            "source": "Scottish Church College",
            "title": title,
            "date": date_text,
            "url": absolute_url,
        })

    logger.info(f"Found {len(notices)} notices from Scottish Church College.")
    return notices


def send_whatsapp_message(session: requests.Session, text_message: str) -> bool:
    """Send a notification message via Official WhatsApp Cloud API."""
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    recipient_phone = os.environ.get("WHATSAPP_RECIPIENT_PHONE_NUMBER")

    if not (token and phone_number_id and recipient_phone):
        logger.warning(
            "WhatsApp Cloud API environment variables (WHATSAPP_TOKEN, "
            "WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_RECIPIENT_PHONE_NUMBER) are not set. "
            "Skipping WhatsApp notification."
        )
        return False

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone,
        "type": "text",
        "text": {"body": text_message},
    }

    try:
        logger.info(f"Sending WhatsApp message to {recipient_phone}...")
        resp = session.post(url, headers=headers, json=payload)
        if resp.status_code in (200, 201):
            logger.info("Successfully sent WhatsApp message.")
            return True
        else:
            logger.error(
                f"WhatsApp Cloud API error [{resp.status_code}]: {resp.text}"
            )
            return False
    except Exception as e:
        logger.error(f"Exception while sending WhatsApp message: {e}")
        return False


def send_telegram_message(session: requests.Session, text_message: str) -> bool:
    """Send a notification message via Telegram Bot API."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not (token and chat_id):
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text_message,
        "disable_web_page_preview": False,
    }

    try:
        logger.info(f"Sending Telegram message to chat {chat_id}...")
        resp = session.post(url, json=payload)
        if resp.status_code in (200, 201):
            logger.info("Successfully sent Telegram message.")
            return True
        else:
            logger.error(f"Telegram API error [{resp.status_code}]: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Exception while sending Telegram message: {e}")
        return False


def send_discord_message(session: requests.Session, text_message: str) -> bool:
    """Send a notification message via Discord Webhook."""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        return False

    payload = {"content": text_message}

    try:
        logger.info("Sending Discord Webhook notification...")
        resp = session.post(webhook_url, json=payload)
        if resp.status_code in (200, 204):
            logger.info("Successfully sent Discord message.")
            return True
        else:
            logger.error(f"Discord Webhook error [{resp.status_code}]: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Exception while sending Discord message: {e}")
        return False


def send_all_notifications(session: requests.Session, text_message: str) -> int:
    """Send notifications to all configured channels (WhatsApp, Telegram, Discord)."""
    sent_count = 0
    if send_whatsapp_message(session, text_message):
        sent_count += 1
    if send_telegram_message(session, text_message):
        sent_count += 1
    if send_discord_message(session, text_message):
        sent_count += 1

    if sent_count == 0:
        logger.warning(
            "No notification channels were triggered (ensure WHATSAPP_TOKEN, "
            "TELEGRAM_BOT_TOKEN+TELEGRAM_CHAT_ID, or DISCORD_WEBHOOK_URL are set)."
        )

    return sent_count


def load_seen_notices(filepath: str) -> set[str]:
    """Load seen notice IDs from JSON persistence file."""
    if not os.path.exists(filepath):
        return set()

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return set(data.get("seen_ids", []))
            elif isinstance(data, list):
                return set(data)
            return set()
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}. Initializing empty set.")
        return set()


def save_seen_notices(filepath: str, seen_ids: set[str]) -> None:
    """Save updated seen notice IDs to JSON file."""
    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_seen": len(seen_ids),
        "seen_ids": sorted(list(seen_ids)),
    }
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(seen_ids)} seen IDs to {filepath}.")
    except Exception as e:
        logger.error(f"Error saving to {filepath}: {e}")


def format_notice_message(notice: dict) -> str:
    """Format a notice into a concise, readable WhatsApp alert message."""
    return (
        "🔔 *New Notice Alert!*\n\n"
        f"🏫 *Source:* {notice['source']}\n"
        f"📅 *Date:* {notice['date']}\n"
        f"📌 *Title:* {notice['title']}\n"
        f"🔗 *Link:* {notice['url']}"
    )


def main():
    parser = argparse.ArgumentParser(description="Notice Scraper & WhatsApp Alerter")
    parser.add_argument(
        "--notify-all",
        action="store_true",
        help="Send WhatsApp alerts for all discovered notices even on initial run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run scrapers without sending WhatsApp messages or modifying JSON state.",
    )
    args = parser.parse_args()

    session = get_http_session()

    # 1. Scrape both sources
    cuexam_notices = scrape_cuexam(session)
    scc_notices = scrape_scottish_church(session)
    all_notices = cuexam_notices + scc_notices

    logger.info(f"Total notices discovered: {len(all_notices)}")

    # 2. Load seen notices
    seen_ids = load_seen_notices(SEEN_FILE)
    is_initial_run = len(seen_ids) == 0

    new_notices = [n for n in all_notices if n["id"] not in seen_ids]
    logger.info(f"New undiscovered notices: {len(new_notices)}")

    if not new_notices:
        logger.info("No new notices found. Everything is up to date.")
        return

    # 3. Handle initial seed vs alert
    if is_initial_run and not args.notify_all:
        logger.info(
            "Initial run detected (0 seen notices previously). Seeding all "
            f"{len(new_notices)} existing notices into {SEEN_FILE} without "
            "sending WhatsApp alerts to prevent message spam."
        )
        if not args.dry_run:
            for notice in new_notices:
                seen_ids.add(notice["id"])
            save_seen_notices(SEEN_FILE, seen_ids)
        return

    # 4. Notify for new notices
    notified_count = 0
    for notice in new_notices:
        message = format_notice_message(notice)
        logger.info(f"Processing new notice: [{notice['source']}] {notice['title']}")

        if args.dry_run:
            logger.info(f"[DRY-RUN] Would send message:\n{message}")
            notified_count += 1
        else:
            send_all_notifications(session, message)
            seen_ids.add(notice["id"])
            notified_count += 1

    if not args.dry_run:
        save_seen_notices(SEEN_FILE, seen_ids)

    logger.info(f"Run completed. Processed {notified_count} new notices.")


if __name__ == "__main__":
    main()
