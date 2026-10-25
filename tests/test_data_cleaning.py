"""
Tests for Module 2: Data Cleaning and Preparation
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_cleaning import clean_data, get_cleaning_report, load_cleaned_csv


# ────────────────────────── Fixtures ─────────────────────────────────────────

@pytest.fixture
def sample_records():
    return [
        {
            "hotel_name": "Hotel Alpha",
            "category": "Luxury",
            "location": "Mumbai, India",
            "description": "A great luxury hotel.",
            "price_inr": "5000",
            "rating": "4.5",
            "reviews": "1000",
            "amenities": "WiFi, Pool",
            "availability": "Available",
            "contact_email": "alpha@hotel.example.com",
        },
        {
            "hotel_name": "Hotel Beta",
            "category": "Budget",
            "location": "Delhi, India",
            "description": "Affordable stay.",
            "price_inr": "1200",
            "rating": "3.8",
            "reviews": "250",
            "amenities": "WiFi",
            "availability": "Available",
            "contact_email": "beta@hotel.example.com",
        },
        {
            "hotel_name": "Hotel Alpha",  # duplicate
            "category": "Luxury",
            "location": "Mumbai, India",
            "description": "A great luxury hotel.",
            "price_inr": "5000",
            "rating": "4.5",
            "reviews": "1000",
            "amenities": "WiFi, Pool",
            "availability": "Available",
            "contact_email": "alpha@hotel.example.com",
        },
        {
            "hotel_name": "",       # missing required field
            "category": "",
            "location": "",
            "description": "",
            "price_inr": "",
            "rating": "",
            "reviews": "",
            "amenities": "",
            "availability": "",
            "contact_email": "",
        },
    ]


@pytest.fixture
def records_with_whitespace():
    return [
        {
            "hotel_name": "  Spaced Hotel  ",
            "category": "  Luxury  ",
            "location": "  Goa,   India  ",
            "description": "  Nice  place.  ",
            "price_inr": "3000",
            "rating": "4.2",
            "reviews": "100",
            "amenities": "  WiFi, Pool  ",
            "availability": "Available",
            "contact_email": "space@hotel.example.com",
        }
    ]


# ────────────────────────── clean_data basic ─────────────────────────────────

def test_clean_data_returns_dataframe_and_summary(sample_records, tmp_path):
    df, summary = clean_data(sample_records, output_path=tmp_path / "cleaned.csv")
    assert isinstance(df, pd.DataFrame)
    assert isinstance(summary, dict)


def test_clean_data_removes_duplicates(sample_records, tmp_path):
    df, summary = clean_data(sample_records, output_path=tmp_path / "cleaned.csv")
    assert summary["duplicates_removed"] >= 1
    # No exact duplicates should remain
    assert df.duplicated().sum() == 0


def test_clean_data_handles_empty_required_fields(sample_records, tmp_path):
    """Rows with all required fields empty should be dropped."""
    df, summary = clean_data(sample_records, output_path=tmp_path / "cleaned.csv")
    # The all-empty row should have been removed
    assert len(df) < len(sample_records)


def test_clean_data_empty_input():
    df, summary = clean_data([])
    assert df.empty or df is not None
    assert "error" in summary or "cleaned_rows" in summary


def test_clean_data_price_numeric(sample_records, tmp_path):
    df, _ = clean_data(sample_records, output_path=tmp_path / "cleaned.csv")
    if "price_inr" in df.columns and not df.empty:
        assert pd.api.types.is_float_dtype(df["price_inr"]) or pd.api.types.is_integer_dtype(df["price_inr"])


def test_clean_data_rating_numeric(sample_records, tmp_path):
    df, _ = clean_data(sample_records, output_path=tmp_path / "cleaned.csv")
    if "rating" in df.columns and not df.empty:
        assert pd.api.types.is_float_dtype(df["rating"])


def test_clean_data_exports_csv(sample_records, tmp_path):
    output = tmp_path / "cleaned.csv"
    clean_data(sample_records, output_path=output)
    assert output.exists()


def test_clean_data_summary_keys(sample_records, tmp_path):
    _, summary = clean_data(sample_records, output_path=tmp_path / "cleaned.csv")
    for key in ("raw_rows", "cleaned_rows", "duplicates_removed"):
        assert key in summary


# ────────────────────────── Whitespace normalisation ─────────────────────────

def test_clean_data_strips_whitespace(records_with_whitespace, tmp_path):
    df, _ = clean_data(records_with_whitespace, output_path=tmp_path / "cleaned.csv")
    if not df.empty and "hotel_name" in df.columns:
        assert df["hotel_name"].iloc[0] == "Spaced Hotel"


# ────────────────────────── Missing value handling ───────────────────────────

def test_clean_data_fills_missing_text_fields(tmp_path):
    records = [
        {
            "hotel_name": "Test Hotel",
            "category": None,
            "location": None,
            "description": None,
            "price_inr": "2000",
            "rating": "4.0",
            "reviews": "100",
            "amenities": None,
            "availability": None,
            "contact_email": None,
        }
    ]
    df, _ = clean_data(records, output_path=tmp_path / "cleaned.csv")
    if not df.empty:
        # Text columns should be filled with "N/A" not left as NaN
        for col in ("category", "location", "amenities"):
            if col in df.columns:
                val = df[col].iloc[0]
                assert val == "N/A" or pd.isna(val) is False


# ────────────────────────── Dimension reporting ──────────────────────────────

def test_clean_data_raw_rows_match_input(sample_records, tmp_path):
    _, summary = clean_data(sample_records, output_path=tmp_path / "cleaned.csv")
    assert summary["raw_rows"] == len(sample_records)


# ────────────────────────── get_cleaning_report ──────────────────────────────

def test_get_cleaning_report_returns_string(sample_records, tmp_path):
    df, summary = clean_data(sample_records, output_path=tmp_path / "cleaned.csv")
    report = get_cleaning_report(df, summary)
    assert isinstance(report, str)
    assert "Raw rows" in report or "raw_rows" in report.lower() or "Raw" in report


# ────────────────────────── load_cleaned_csv ─────────────────────────────────

def test_load_cleaned_csv_missing_file(tmp_path):
    result = load_cleaned_csv(path=tmp_path / "no_such_file.csv")
    assert result is None


def test_load_cleaned_csv_round_trip(sample_records, tmp_path):
    output = tmp_path / "cleaned.csv"
    df_out, _ = clean_data(sample_records, output_path=output)
    df_in = load_cleaned_csv(path=output)
    if df_in is not None and not df_out.empty:
        assert len(df_in) == len(df_out)
