"""
Tests for Module 1: Data Collection
"""

import sys
from pathlib import Path

import pytest

# Allow importing from src/ without installing as a package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_collection import (
    _extract_hotel_card,
    _safe_text,
    load_fallback_csv,
    parse_local_html,
    save_raw_csv,
)
from bs4 import BeautifulSoup


# ────────────────────────── Fixtures ─────────────────────────────────────────

SAMPLE_CARD_HTML = """
<div class="hotel-card" id="hotel-99">
  <h2 class="hotel-name">Test Grand Hotel</h2>
  <span class="category">Luxury</span>
  <p class="location">Test City, India</p>
  <p class="description">A wonderful test hotel for pytest purposes.</p>
  <span class="price">₹4,999</span>
  <span class="currency">INR</span>
  <span class="per-night">per night</span>
  <span class="rating">4.5</span>
  <span class="reviews">500 reviews</span>
  <span class="amenities">WiFi, Pool, Gym</span>
  <span class="availability">Available</span>
  <a class="contact-email" href="mailto:test@grandhotel.example.com">test@grandhotel.example.com</a>
</div>
"""

MISSING_NAME_CARD_HTML = """
<div class="hotel-card" id="hotel-bad">
  <span class="category">Budget</span>
  <p class="location">Unknown City</p>
  <span class="price">₹500</span>
</div>
"""

MALFORMED_HTML = "<div><h2 class='hotel-name'></h2><span class='price'>not-a-number</span></div>"


# ────────────────────────── _safe_text ───────────────────────────────────────

def test_safe_text_normal():
    soup = BeautifulSoup("<p>Hello  World</p>", "lxml")
    assert _safe_text(soup.find("p")) == "Hello  World"


def test_safe_text_none():
    assert _safe_text(None) == ""


def test_safe_text_empty_tag():
    soup = BeautifulSoup("<p></p>", "lxml")
    assert _safe_text(soup.find("p")) == ""


# ────────────────────────── _extract_hotel_card ──────────────────────────────

def test_extract_hotel_card_valid():
    soup = BeautifulSoup(SAMPLE_CARD_HTML, "lxml")
    card = soup.find("div", class_="hotel-card")
    record = _extract_hotel_card(card)

    assert record is not None
    assert record["hotel_name"] == "Test Grand Hotel"
    assert record["category"] == "Luxury"
    assert record["location"] == "Test City, India"
    assert record["price_inr"] == "4999"
    assert record["rating"] == "4.5"
    assert record["reviews"] == "500 reviews"
    assert record["contact_email"] == "test@grandhotel.example.com"


def test_extract_hotel_card_missing_name_returns_none():
    soup = BeautifulSoup(MISSING_NAME_CARD_HTML, "lxml")
    card = soup.find("div", class_="hotel-card")
    result = _extract_hotel_card(card)
    assert result is None


def test_extract_hotel_card_malformed_html():
    """Malformed HTML should not raise an exception — return None or partial."""
    soup = BeautifulSoup(MALFORMED_HTML, "lxml")
    card = soup.find("div")
    # Should not crash; may return None (no hotel name)
    result = _extract_hotel_card(card)
    assert result is None or isinstance(result, dict)


# ────────────────────────── parse_local_html ─────────────────────────────────

def test_parse_local_html_returns_list():
    records = parse_local_html()
    assert isinstance(records, list)


def test_parse_local_html_minimum_records():
    """Bundled HTML must have at least 5 hotel cards."""
    records = parse_local_html()
    assert len(records) >= 5


def test_parse_local_html_record_fields():
    """Each record must contain the expected keys."""
    records = parse_local_html()
    assert len(records) > 0
    expected_keys = {
        "hotel_name", "category", "location", "description",
        "price_inr", "rating", "reviews", "amenities",
        "availability", "contact_email",
    }
    for record in records:
        assert expected_keys.issubset(set(record.keys()))


def test_parse_local_html_no_empty_names():
    """All parsed records should have non-empty hotel names."""
    records = parse_local_html()
    for r in records:
        assert r["hotel_name"].strip() != ""


def test_parse_local_html_missing_file(tmp_path):
    """Parsing a non-existent file should return an empty list, not raise."""
    result = parse_local_html(html_path=tmp_path / "nonexistent.html")
    assert result == []


# ────────────────────────── load_fallback_csv ────────────────────────────────

def test_load_fallback_csv_returns_list():
    records = load_fallback_csv()
    assert isinstance(records, list)
    assert len(records) > 0


def test_load_fallback_csv_has_expected_columns():
    records = load_fallback_csv()
    assert "hotel_name" in records[0]
    assert "price_inr" in records[0]
    assert "rating" in records[0]


def test_load_fallback_csv_missing_file(tmp_path):
    result = load_fallback_csv(csv_path=tmp_path / "missing.csv")
    assert result == []


# ────────────────────────── save_raw_csv ─────────────────────────────────────

def test_save_raw_csv_creates_file(tmp_path):
    records = [
        {"hotel_name": "Test", "price_inr": "1000", "rating": "4.0"},
    ]
    output_path = tmp_path / "raw.csv"
    result = save_raw_csv(records, output_path=output_path)
    assert output_path.exists()
    assert result == output_path


def test_save_raw_csv_empty_records(tmp_path):
    output_path = tmp_path / "raw_empty.csv"
    save_raw_csv([], output_path=output_path)
    # File should not be created for empty records
    assert not output_path.exists()
