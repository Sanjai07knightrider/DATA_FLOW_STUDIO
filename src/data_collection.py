"""
Module 1: Data Collection
=========================
Collects hotel advertisement data from:
  1. A bundled local HTML file (sample_page.html) — always available.
  2. A permitted public web page (books.toscrape.com) — requires internet.

The module respects robots.txt guidance, uses request timeouts,
provides polite headers, and never bypasses authentication or CAPTCHAs.
"""

import csv
import logging
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ─────────────────────────── Logging ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────── Constants ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LOCAL_HTML = DATA_DIR / "sample_page.html"
FALLBACK_CSV = DATA_DIR / "sample_data.csv"
RAW_OUTPUT_CSV = OUTPUT_DIR / "raw_collected_data.csv"

# Public demo site — no login, no CAPTCHA, scraping explicitly permitted
DEMO_URL = "https://books.toscrape.com/"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Educational-Demo-Bot/1.0; "
        "+https://github.com/example/web-data-email-system)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_TIMEOUT = 15  # seconds
RATE_LIMIT_DELAY = 1.0  # seconds between requests


# ─────────────────────────── Local HTML Parser ───────────────────────────────
def parse_local_html(html_path: Path = LOCAL_HTML) -> list[dict]:
    """
    Parse the bundled sample_page.html and return a list of hotel record dicts.
    This method works offline and is the primary demonstration source.
    """
    if not html_path.exists():
        logger.error("Local HTML file not found: %s", html_path)
        return []

    logger.info("Parsing local HTML file: %s", html_path)
    with open(html_path, encoding="utf-8") as fh:
        soup = BeautifulSoup(fh.read(), "lxml")

    records = []
    cards = soup.find_all("div", class_="hotel-card")
    logger.info("Found %d hotel card(s) in local HTML.", len(cards))

    for card in cards:
        record = _extract_hotel_card(card)
        if record:
            records.append(record)

    logger.info("Parsed %d valid record(s) from local HTML.", len(records))
    return records


def _extract_hotel_card(card) -> Optional[dict]:
    """Extract fields from a single hotel-card <div>."""
    try:
        name_tag = card.find("h2", class_="hotel-name")
        hotel_name = _safe_text(name_tag)
        if not hotel_name:
            logger.warning("Skipping card — hotel name is missing.")
            return None

        price_raw = _safe_text(card.find("span", class_="price"))
        price_clean = price_raw.replace("₹", "").replace(",", "").strip() if price_raw else ""

        return {
            "hotel_name": hotel_name,
            "category": _safe_text(card.find("span", class_="category")),
            "location": _safe_text(card.find("p", class_="location")),
            "description": _safe_text(card.find("p", class_="description")),
            "price_inr": price_clean,
            "rating": _safe_text(card.find("span", class_="rating")),
            "reviews": _safe_text(card.find("span", class_="reviews")).replace(",", ""),
            "amenities": _safe_text(card.find("span", class_="amenities")),
            "availability": _safe_text(card.find("span", class_="availability")),
            "contact_email": _safe_text(card.find("a", class_="contact-email")),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error extracting hotel card: %s", exc)
        return None


def _safe_text(tag) -> str:
    """Return stripped text from a BS4 tag, or empty string if tag is None."""
    if tag is None:
        return ""
    return tag.get_text(strip=True)


# ─────────────────────────── Online Data Fetcher ────────────────────────────
def fetch_online_books(max_pages: int = 2) -> list[dict]:
    """
    Fetch book listings from books.toscrape.com (publicly permitted demo site).
    Returns a list of dicts with title, price, rating, availability fields.

    This demonstrates internet-based scraping in an ethical, permitted manner.
    books.toscrape.com was built specifically for scraping practice.
    """
    logger.info("Fetching data from %s (max %d page(s))…", DEMO_URL, max_pages)
    all_records = []
    current_url = DEMO_URL
    pages_fetched = 0

    while current_url and pages_fetched < max_pages:
        try:
            logger.info("  → Requesting page: %s", current_url)
            response = requests.get(
                current_url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error("Request timed out for URL: %s", current_url)
            break
        except requests.exceptions.HTTPError as exc:
            logger.error("HTTP error %s for URL: %s", exc.response.status_code, current_url)
            break
        except requests.exceptions.ConnectionError:
            logger.error("Connection error — internet may be unavailable.")
            break

        soup = BeautifulSoup(response.text, "lxml")
        books = soup.find_all("article", class_="product_pod")
        logger.info("  → Found %d book(s) on this page.", len(books))

        for book in books:
            record = _extract_book(book)
            if record:
                all_records.append(record)

        # Follow pagination — respect the site's natural navigation
        next_btn = soup.select_one("li.next a")
        if next_btn:
            next_href = next_btn.get("href", "")
            if pages_fetched == 0:
                current_url = DEMO_URL + "catalogue/" + next_href
            else:
                base = current_url.rsplit("/", 1)[0]
                current_url = base + "/" + next_href
        else:
            current_url = None

        pages_fetched += 1
        if current_url:
            time.sleep(RATE_LIMIT_DELAY)  # polite rate limiting

    logger.info("Online fetch complete — %d record(s) retrieved.", len(all_records))
    return all_records


def _extract_book(article) -> Optional[dict]:
    """Extract fields from a books.toscrape.com <article> element."""
    try:
        title_tag = article.select_one("h3 a")
        title = title_tag.get("title", _safe_text(title_tag)) if title_tag else ""
        if not title:
            return None

        price_tag = article.select_one("p.price_color")
        price_raw = _safe_text(price_tag).replace("Â", "").replace("£", "").strip()

        avail_tag = article.select_one("p.availability")
        availability = _safe_text(avail_tag)

        rating_map = {
            "One": "1", "Two": "2", "Three": "3", "Four": "4", "Five": "5",
        }
        rating_tag = article.select_one("p.star-rating")
        rating_word = rating_tag.get("class", ["", ""])[1] if rating_tag else ""
        rating = rating_map.get(rating_word, "")

        return {
            "hotel_name": title,          # reuse column name for uniform schema
            "category": "Book",
            "location": "Online Catalogue",
            "description": f"Book listing from books.toscrape.com — {title}",
            "price_inr": price_raw,
            "rating": rating,
            "reviews": "",
            "amenities": "",
            "availability": availability,
            "contact_email": "",
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error parsing book article: %s", exc)
        return None


# ─────────────────────────── Fallback CSV Loader ────────────────────────────
def load_fallback_csv(csv_path: Path = FALLBACK_CSV) -> list[dict]:
    """
    Load the pre-bundled sample_data.csv as a guaranteed offline fallback.
    This ensures the application is always demonstrable without internet.
    """
    if not csv_path.exists():
        logger.error("Fallback CSV not found: %s", csv_path)
        return []

    logger.info("Loading fallback dataset from: %s", csv_path)
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        records = [dict(row) for row in reader]

    logger.info("Loaded %d record(s) from fallback CSV.", len(records))
    return records


# ─────────────────────────── Export Helper ──────────────────────────────────
def save_raw_csv(records: list[dict], output_path: Path = RAW_OUTPUT_CSV) -> Path:
    """
    Save the raw collected records to a CSV file (before any cleaning).
    Raw data is preserved separately from cleaned data.
    """
    if not records:
        logger.warning("No records to save.")
        return output_path

    fieldnames = list(records[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    logger.info("Raw data saved to: %s (%d records)", output_path, len(records))
    return output_path


# ─────────────────────────── Main Entry ─────────────────────────────────────
def collect_data(source: str = "local") -> list[dict]:
    """
    Primary entry point for data collection.

    Args:
        source: "local"    — parse sample_page.html (offline, always works)
                "online"   — fetch from books.toscrape.com (requires internet)
                "fallback" — load pre-bundled sample_data.csv

    Returns:
        List of record dicts.
    """
    source = source.strip().lower()

    if source == "local":
        records = parse_local_html()
    elif source == "online":
        records = fetch_online_books()
        if not records:
            logger.warning("Online fetch returned no data. Falling back to local HTML.")
            records = parse_local_html()
    elif source == "fallback":
        records = load_fallback_csv()
    else:
        logger.error("Unknown source '%s'. Using local HTML.", source)
        records = parse_local_html()

    if records:
        save_raw_csv(records)

    return records


if __name__ == "__main__":
    data = collect_data("local")
    print(f"\nCollected {len(data)} records.")
    if data:
        print("Sample record:")
        for k, v in data[0].items():
            print(f"  {k}: {v}")
