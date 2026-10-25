"""
Tests for Module 3: Synthetic Data Generation
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.synthetic_data import generate_synthetic_data, get_synthetic_summary


# ────────────────────────── Fixtures ─────────────────────────────────────────

@pytest.fixture
def reference_df():
    return pd.DataFrame([
        {
            "hotel_name": "Hotel Alpha",
            "category": "Luxury",
            "location": "Mumbai, India",
            "description": "Luxury stay.",
            "price_inr": 5000.0,
            "rating": 4.5,
            "reviews": 1000,
            "amenities": "WiFi, Pool",
            "availability": "Available",
            "contact_email": "alpha@hotel.example.com",
        },
        {
            "hotel_name": "Budget Inn",
            "category": "Budget",
            "location": "Delhi, India",
            "description": "Affordable.",
            "price_inr": 1200.0,
            "rating": 3.8,
            "reviews": 200,
            "amenities": "WiFi",
            "availability": "Available",
            "contact_email": "budget@inn.example.com",
        },
    ])


# ────────────────────────── Basic generation ─────────────────────────────────

def test_generate_returns_dataframe(reference_df, tmp_path):
    df = generate_synthetic_data(reference_df, n_records=5, seed=42,
                                  output_path=tmp_path / "syn.csv")
    assert isinstance(df, pd.DataFrame)


def test_generate_correct_count(reference_df, tmp_path):
    n = 15
    df = generate_synthetic_data(reference_df, n_records=n, seed=42,
                                  output_path=tmp_path / "syn.csv")
    assert len(df) == n


def test_generate_zero_records(reference_df, tmp_path):
    df = generate_synthetic_data(reference_df, n_records=0, seed=42,
                                  output_path=tmp_path / "syn0.csv")
    assert len(df) == 0


def test_generate_with_empty_reference(tmp_path):
    """Should not crash with an empty reference DataFrame."""
    empty_df = pd.DataFrame()
    df = generate_synthetic_data(empty_df, n_records=5, seed=1,
                                  output_path=tmp_path / "syn_empty.csv")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5


# ────────────────────────── SYNTHETIC label ──────────────────────────────────

def test_generate_all_records_labelled_synthetic(reference_df, tmp_path):
    df = generate_synthetic_data(reference_df, n_records=10, seed=42,
                                  output_path=tmp_path / "syn.csv")
    assert "record_type" in df.columns
    assert (df["record_type"] == "SYNTHETIC").all()


# ────────────────────────── Reproducibility ──────────────────────────────────

def test_generate_reproducible_with_same_seed(reference_df, tmp_path):
    df1 = generate_synthetic_data(reference_df, n_records=5, seed=99,
                                   output_path=tmp_path / "syn1.csv")
    df2 = generate_synthetic_data(reference_df, n_records=5, seed=99,
                                   output_path=tmp_path / "syn2.csv")
    pd.testing.assert_frame_equal(df1.reset_index(drop=True),
                                   df2.reset_index(drop=True))


def test_generate_different_seeds_differ(reference_df, tmp_path):
    df1 = generate_synthetic_data(reference_df, n_records=10, seed=1,
                                   output_path=tmp_path / "syn_a.csv")
    df2 = generate_synthetic_data(reference_df, n_records=10, seed=2,
                                   output_path=tmp_path / "syn_b.csv")
    # Very unlikely to be identical with different seeds
    assert not df1["hotel_name"].equals(df2["hotel_name"])


# ────────────────────────── Column presence ──────────────────────────────────

def test_generate_has_required_columns(reference_df, tmp_path):
    df = generate_synthetic_data(reference_df, n_records=5, seed=42,
                                  output_path=tmp_path / "syn.csv")
    for col in ("hotel_name", "category", "price_inr", "rating", "record_type"):
        assert col in df.columns


# ────────────────────────── No personal data copied ──────────────────────────

def test_generate_no_real_emails_copied(reference_df, tmp_path):
    """Synthetic emails should differ from reference emails."""
    real_emails = set(reference_df["contact_email"].tolist())
    df = generate_synthetic_data(reference_df, n_records=20, seed=42,
                                  output_path=tmp_path / "syn.csv")
    for email in df["contact_email"]:
        assert email not in real_emails


def test_generate_synthetic_emails_use_example_domain(reference_df, tmp_path):
    df = generate_synthetic_data(reference_df, n_records=10, seed=42,
                                  output_path=tmp_path / "syn.csv")
    for email in df["contact_email"]:
        assert "synthetic.example.com" in email


# ────────────────────────── CSV export ───────────────────────────────────────

def test_generate_exports_csv(reference_df, tmp_path):
    output = tmp_path / "syn_out.csv"
    generate_synthetic_data(reference_df, n_records=5, seed=42, output_path=output)
    assert output.exists()


# ────────────────────────── get_synthetic_summary ────────────────────────────

def test_get_synthetic_summary_keys(reference_df, tmp_path):
    df = generate_synthetic_data(reference_df, n_records=10, seed=42,
                                  output_path=tmp_path / "syn.csv")
    summary = get_synthetic_summary(df)
    assert "total_records" in summary
    assert summary["total_records"] == 10
    assert "label" in summary
    assert "SYNTHETIC" in summary["label"]


def test_get_synthetic_summary_empty():
    summary = get_synthetic_summary(pd.DataFrame())
    assert "error" in summary
