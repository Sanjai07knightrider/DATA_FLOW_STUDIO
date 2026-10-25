"""
Tests for CSV upload validation (validate_uploaded_csv, apply_column_fixes).
All tests use in-memory DataFrames — no file uploads, no internet required.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.validation import (
    validate_uploaded_csv,
    apply_column_fixes,
    ALL_KNOWN_COLUMNS,
    MAX_UPLOAD_ROWS,
    MAX_UPLOAD_MB,
)


# ─────────────────────────── Fixtures ────────────────────────────────────────

@pytest.fixture
def valid_df():
    """Minimal valid upload DataFrame with all schema columns."""
    return pd.DataFrame([
        {
            "hotel_name":    "Hotel Alpha",
            "category":      "Luxury",
            "location":      "Mumbai, India",
            "description":   "A wonderful hotel.",
            "price_inr":     "5000",
            "rating":        "4.5",
            "reviews":       "1000",
            "amenities":     "WiFi, Pool",
            "availability":  "Available",
            "contact_email": "alpha@hotel.example.com",
        },
        {
            "hotel_name":    "Budget Stay",
            "category":      "Budget",
            "location":      "Delhi, India",
            "description":   "Affordable.",
            "price_inr":     "1200",
            "rating":        "3.8",
            "reviews":       "200",
            "amenities":     "WiFi",
            "availability":  "Available",
            "contact_email": "budget@stay.example.com",
        },
    ])


@pytest.fixture
def minimal_df():
    """DataFrame with only the required hotel_name column."""
    return pd.DataFrame([
        {"hotel_name": "Solo Hotel"},
        {"hotel_name": "Duo Inn"},
    ])


@pytest.fixture
def alias_df():
    """DataFrame with aliased column names instead of canonical names."""
    return pd.DataFrame([
        {
            "name":           "Alias Hotel",
            "type":           "Boutique",
            "city":           "Goa, India",
            "about":          "Near the beach.",
            "price":          "3500",
            "stars":          "4.2",
            "review_count":   "350",
            "facilities":     "Beach, WiFi",
            "status":         "Available",
            "email":          "alias@hotel.example.com",
        }
    ])


@pytest.fixture
def missing_name_df():
    """DataFrame that lacks hotel_name and any recognised alias."""
    return pd.DataFrame([
        {"property_id": "001", "tariff": "5000", "grade": "A+"},
        {"property_id": "002", "tariff": "3000", "grade": "B"},
    ])


@pytest.fixture
def no_email_df():
    """DataFrame with hotel_name but no contact_email or alias."""
    return pd.DataFrame([
        {"hotel_name": "Hotel No Email", "category": "Budget", "price_inr": "1000"},
    ])


@pytest.fixture
def duplicate_df():
    """DataFrame with duplicate rows."""
    row = {"hotel_name": "Dup Hotel", "contact_email": "dup@hotel.example.com"}
    return pd.DataFrame([row, row, row])


@pytest.fixture
def all_null_col_df():
    """DataFrame with one completely empty column."""
    return pd.DataFrame([
        {"hotel_name": "Null Col Hotel", "category": "", "contact_email": "a@b.example.com"},
        {"hotel_name": "Another Hotel",  "category": "", "contact_email": "c@d.example.com"},
    ])


@pytest.fixture
def mixed_case_df():
    """DataFrame where column names have wrong casing."""
    return pd.DataFrame([
        {
            "Hotel_Name":    "CaseHotel",
            "CATEGORY":      "Luxury",
            "Contact_Email": "case@hotel.example.com",
        }
    ])


# ─────────────────────────── validate_uploaded_csv ───────────────────────────

class TestValidateUploadedCsv:

    # ── Valid inputs ─────────────────────────────────────────────────────────

    def test_valid_full_schema_df_passes(self, valid_df):
        vr = validate_uploaded_csv(valid_df, filename="test.csv", size_bytes=1024)
        assert vr["valid"] is True
        assert vr["errors"] == []

    def test_valid_minimal_df_passes(self, minimal_df):
        """A DataFrame with only hotel_name should be valid (all others optional)."""
        vr = validate_uploaded_csv(minimal_df, filename="minimal.csv")
        assert vr["valid"] is True

    def test_returns_correct_row_col_counts(self, valid_df):
        vr = validate_uploaded_csv(valid_df, filename="test.csv")
        assert vr["row_count"] == 2
        assert vr["col_count"] == 10

    def test_present_cols_detected(self, valid_df):
        vr = validate_uploaded_csv(valid_df, filename="test.csv")
        assert "hotel_name"    in vr["present_cols"]
        assert "contact_email" in vr["present_cols"]
        assert "price_inr"     in vr["present_cols"]

    def test_no_missing_known_cols_when_full(self, valid_df):
        vr = validate_uploaded_csv(valid_df, filename="test.csv")
        assert vr["missing_cols"] == []

    # ── Empty / null inputs ──────────────────────────────────────────────────

    def test_empty_dataframe_fails(self):
        vr = validate_uploaded_csv(pd.DataFrame(), filename="empty.csv")
        assert vr["valid"] is False
        assert any("no data rows" in e.lower() for e in vr["errors"])

    def test_none_dataframe_fails(self):
        vr = validate_uploaded_csv(None, filename="none.csv")
        assert vr["valid"] is False
        assert len(vr["errors"]) > 0

    # ── Row limit ────────────────────────────────────────────────────────────

    def test_row_limit_exceeded_fails(self):
        big_df = pd.DataFrame(
            [{"hotel_name": f"H{i}"} for i in range(MAX_UPLOAD_ROWS + 1)]
        )
        vr = validate_uploaded_csv(big_df, filename="big.csv")
        assert vr["valid"] is False
        assert any(str(MAX_UPLOAD_ROWS) in e or "rows" in e.lower() for e in vr["errors"])

    def test_row_limit_at_boundary_passes(self):
        boundary_df = pd.DataFrame(
            [{"hotel_name": f"H{i}"} for i in range(MAX_UPLOAD_ROWS)]
        )
        vr = validate_uploaded_csv(boundary_df, filename="boundary.csv")
        # Should not error on row count (may have other issues but not the limit)
        assert not any(str(MAX_UPLOAD_ROWS) in e for e in vr["errors"])

    # ── File size ────────────────────────────────────────────────────────────

    def test_oversized_file_fails(self, valid_df):
        oversized = MAX_UPLOAD_MB * 1024 * 1024 + 1
        vr = validate_uploaded_csv(valid_df, filename="big.csv", size_bytes=oversized)
        assert vr["valid"] is False
        assert any("MB" in e or "limit" in e.lower() for e in vr["errors"])

    def test_normal_size_passes(self, valid_df):
        vr = validate_uploaded_csv(valid_df, filename="ok.csv", size_bytes=1024)
        assert vr["valid"] is True

    # ── Required column: hotel_name ──────────────────────────────────────────

    def test_missing_hotel_name_fails(self, missing_name_df):
        vr = validate_uploaded_csv(missing_name_df, filename="bad.csv")
        assert vr["valid"] is False
        assert any("hotel_name" in e for e in vr["errors"])

    def test_error_message_lists_actual_columns(self, missing_name_df):
        vr = validate_uploaded_csv(missing_name_df, filename="bad.csv")
        error_text = " ".join(vr["errors"])
        # The error should mention what columns were actually found
        assert "property_id" in error_text or "tariff" in error_text or "columns" in error_text.lower()

    # ── Alias detection ──────────────────────────────────────────────────────

    def test_alias_name_column_passes(self, alias_df):
        """'name' is a recognised alias for hotel_name — file should be valid."""
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        assert vr["valid"] is True
        assert vr["errors"] == []

    def test_alias_map_populated(self, alias_df):
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        assert len(vr["alias_map"]) > 0
        assert "hotel_name" in vr["alias_map"].values()

    def test_alias_email_detected(self, alias_df):
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        assert "contact_email" in vr["alias_map"].values()

    def test_alias_price_detected(self, alias_df):
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        assert "price_inr" in vr["alias_map"].values()

    def test_alias_rating_detected(self, alias_df):
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        assert "rating" in vr["alias_map"].values()

    def test_alias_location_detected(self, alias_df):
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        assert "location" in vr["alias_map"].values()

    # ── Warnings ─────────────────────────────────────────────────────────────

    def test_missing_contact_email_warns(self, no_email_df):
        vr = validate_uploaded_csv(no_email_df, filename="noemail.csv")
        assert vr["valid"] is True   # not a blocking error
        assert any("contact_email" in w for w in vr["warnings"])

    def test_duplicate_rows_warns(self, duplicate_df):
        vr = validate_uploaded_csv(duplicate_df, filename="dup.csv")
        assert any("duplicate" in w.lower() for w in vr["warnings"])
        assert vr["valid"] is True   # duplicates are a warning, not an error

    def test_all_null_column_warns(self, all_null_col_df):
        vr = validate_uploaded_csv(all_null_col_df, filename="nullcol.csv")
        assert any("category" in w for w in vr["warnings"])

    # ── Extra columns ────────────────────────────────────────────────────────

    def test_extra_columns_detected(self):
        df = pd.DataFrame([
            {"hotel_name": "H1", "mystery_col": "xyz", "another_extra": "abc"}
        ])
        vr = validate_uploaded_csv(df, filename="extra.csv")
        assert "mystery_col" in vr["extra_cols"] or "another_extra" in vr["extra_cols"]
        assert vr["valid"] is True   # extra columns are allowed

    # ── Case-insensitive column matching ─────────────────────────────────────

    def test_mixed_case_columns_accepted(self, mixed_case_df):
        """Columns like Hotel_Name should match hotel_name case-insensitively."""
        vr = validate_uploaded_csv(mixed_case_df, filename="case.csv")
        assert vr["valid"] is True
        assert "hotel_name" in vr["present_cols"]

    # ── Info messages ─────────────────────────────────────────────────────────

    def test_info_contains_filename(self, valid_df):
        vr = validate_uploaded_csv(valid_df, filename="myfile.csv")
        assert any("myfile.csv" in msg for msg in vr["info"])

    def test_info_contains_row_count(self, valid_df):
        vr = validate_uploaded_csv(valid_df, filename="test.csv")
        assert any("2" in msg for msg in vr["info"])

    def test_alias_info_message_shown(self, alias_df):
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        assert any("alias" in msg.lower() or "renamed" in msg.lower() for msg in vr["info"])


# ─────────────────────────── apply_column_fixes ──────────────────────────────

class TestApplyColumnFixes:

    def test_alias_columns_renamed(self, alias_df):
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        fixed = apply_column_fixes(alias_df, vr)
        assert "hotel_name"    in fixed.columns
        assert "contact_email" in fixed.columns
        assert "price_inr"     in fixed.columns

    def test_original_df_not_mutated(self, alias_df):
        original_cols = list(alias_df.columns)
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        apply_column_fixes(alias_df, vr)
        # Original must be unchanged
        assert list(alias_df.columns) == original_cols

    def test_case_fix_applied(self, mixed_case_df):
        vr = validate_uploaded_csv(mixed_case_df, filename="case.csv")
        fixed = apply_column_fixes(mixed_case_df, vr)
        assert "hotel_name"    in fixed.columns
        assert "contact_email" in fixed.columns
        # Old cased versions should be gone
        assert "Hotel_Name"    not in fixed.columns
        assert "Contact_Email" not in fixed.columns

    def test_extra_cols_preserved(self):
        df = pd.DataFrame([{"hotel_name": "H", "my_extra_col": "val"}])
        vr = validate_uploaded_csv(df, filename="extra.csv")
        fixed = apply_column_fixes(df, vr)
        assert "my_extra_col" in fixed.columns
        assert "hotel_name"   in fixed.columns

    def test_no_changes_needed_leaves_df_intact(self, valid_df):
        vr = validate_uploaded_csv(valid_df, filename="valid.csv")
        fixed = apply_column_fixes(valid_df, vr)
        assert list(fixed.columns) == list(valid_df.columns)

    def test_data_values_preserved_after_rename(self, alias_df):
        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        fixed = apply_column_fixes(alias_df, vr)
        assert fixed["hotel_name"].iloc[0] == "Alias Hotel"


# ─────────────────────────── Upload-to-pipeline integration ──────────────────

class TestUploadToPipelineIntegration:
    """
    Verify that an uploaded CSV, once validated and column-fixed,
    can be passed directly through the cleaning and synthetic data modules.
    """

    def test_upload_through_cleaning_pipeline(self, valid_df, tmp_path):
        """Validated + fixed upload DF should clean without errors."""
        from src.data_cleaning import clean_data

        vr = validate_uploaded_csv(valid_df, filename="valid.csv")
        assert vr["valid"]

        fixed_df = apply_column_fixes(valid_df, vr)
        records  = fixed_df.to_dict(orient="records")
        df_clean, summary = clean_data(records, output_path=tmp_path / "cleaned.csv")

        assert not df_clean.empty
        assert "cleaned_rows" in summary
        assert summary["cleaned_rows"] > 0

    def test_alias_upload_through_cleaning_pipeline(self, alias_df, tmp_path):
        """Alias-named upload should work end-to-end through cleaning."""
        from src.data_cleaning import clean_data

        vr = validate_uploaded_csv(alias_df, filename="alias.csv")
        assert vr["valid"]

        fixed_df = apply_column_fixes(alias_df, vr)
        records  = fixed_df.to_dict(orient="records")
        df_clean, summary = clean_data(records, output_path=tmp_path / "cleaned.csv")

        assert not df_clean.empty
        assert "hotel_name" in df_clean.columns

    def test_upload_through_synthetic_generation(self, valid_df, tmp_path):
        """Cleaned upload data should produce synthetic records."""
        from src.data_cleaning  import clean_data
        from src.synthetic_data import generate_synthetic_data

        vr = validate_uploaded_csv(valid_df, filename="valid.csv")
        fixed_df = apply_column_fixes(valid_df, vr)
        records  = fixed_df.to_dict(orient="records")
        df_clean, _ = clean_data(records, output_path=tmp_path / "cleaned.csv")

        syn_df = generate_synthetic_data(
            df_clean, n_records=5, seed=42,
            output_path=tmp_path / "syn.csv",
        )
        assert len(syn_df) == 5
        assert (syn_df["record_type"] == "SYNTHETIC").all()

    def test_upload_through_email_drafts(self, valid_df, tmp_path):
        """Upload with contact_email should produce email drafts."""
        from src.data_cleaning    import clean_data
        from src.email_automation import generate_email_drafts

        vr = validate_uploaded_csv(valid_df, filename="valid.csv")
        fixed_df = apply_column_fixes(valid_df, vr)
        records  = fixed_df.to_dict(orient="records")
        df_clean, _ = clean_data(records, output_path=tmp_path / "cleaned.csv")

        drafts, skipped = generate_email_drafts(
            df_clean,
            max_drafts=10,
            export_eml=False,
            output_csv=tmp_path / "drafts.csv",
        )
        assert len(drafts) >= 1
        assert all("draft_id" in d for d in drafts)

    def test_upload_without_email_col_skips_drafts(self, no_email_df, tmp_path):
        """Upload without contact_email should produce zero drafts (all skipped)."""
        from src.data_cleaning    import clean_data
        from src.email_automation import generate_email_drafts

        vr = validate_uploaded_csv(no_email_df, filename="noemail.csv")
        fixed_df = apply_column_fixes(no_email_df, vr)
        records  = fixed_df.to_dict(orient="records")
        df_clean, _ = clean_data(records, output_path=tmp_path / "cleaned.csv")

        drafts, skipped = generate_email_drafts(
            df_clean,
            max_drafts=10,
            export_eml=False,
            output_csv=tmp_path / "drafts_none.csv",
        )
        assert len(drafts) == 0
        assert len(skipped) >= 1

    def test_original_upload_preserved_separately(self, valid_df, tmp_path):
        """Original uploaded CSV should be saved separately from processed outputs."""
        vr = validate_uploaded_csv(valid_df, filename="mydata.csv")
        fixed_df = apply_column_fixes(valid_df, vr)

        original_path = tmp_path / "uploaded_original_mydata.csv"
        fixed_df.to_csv(original_path, index=False)

        # Simulate cleaning (which writes to a different path)
        from src.data_cleaning import clean_data
        cleaned_path = tmp_path / "cleaned_data.csv"
        records = fixed_df.to_dict(orient="records")
        clean_data(records, output_path=cleaned_path)

        # Both files should exist and be distinct
        assert original_path.exists()
        assert cleaned_path.exists()

        original_read = pd.read_csv(original_path)
        # Original has the raw string values; cleaning may change types
        # Just verify the files are both readable and non-empty
        assert len(original_read) == len(valid_df)
