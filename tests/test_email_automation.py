"""
Tests for Module 4: Email Draft Generation
and Module 5: Validation Utilities
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.email_automation import (
    generate_email_drafts,
    preview_draft,
    render_template,
    send_draft_via_smtp,
)
from src.validation import (
    is_valid_email,
    sanitise_email,
    validate_dataframe,
    validate_price,
    validate_records,
)


# ════════════════════════════════════════════════════════════════════════════
# Validation tests
# ════════════════════════════════════════════════════════════════════════════

class TestIsValidEmail:
    def test_valid_simple(self):
        assert is_valid_email("user@example.com") is True

    def test_valid_subdomain(self):
        assert is_valid_email("user@mail.example.co.in") is True

    def test_valid_plus_tag(self):
        assert is_valid_email("user+tag@domain.org") is True

    def test_invalid_no_at(self):
        assert is_valid_email("notanemail") is False

    def test_invalid_no_domain(self):
        assert is_valid_email("user@") is False

    def test_invalid_no_tld(self):
        assert is_valid_email("user@nodot") is False

    def test_invalid_empty_string(self):
        assert is_valid_email("") is False

    def test_invalid_none(self):
        assert is_valid_email(None) is False

    def test_invalid_spaces(self):
        assert is_valid_email("has spaces@example.com") is False

    def test_invalid_double_at(self):
        assert is_valid_email("a@@example.com") is False


class TestSanitiseEmail:
    def test_lowercase(self):
        assert sanitise_email("User@Example.COM") == "user@example.com"

    def test_strip_spaces(self):
        assert sanitise_email("  user@example.com  ") == "user@example.com"

    def test_invalid_returns_empty(self):
        assert sanitise_email("bad-email") == ""

    def test_none_returns_empty(self):
        assert sanitise_email(None) == ""


class TestValidateDataFrame:
    def test_valid_df(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        ok, errors = validate_dataframe(df, required_columns=["a", "b"])
        assert ok is True
        assert errors == []

    def test_missing_column(self):
        df = pd.DataFrame({"a": [1]})
        ok, errors = validate_dataframe(df, required_columns=["a", "z"])
        assert ok is False
        assert any("z" in e for e in errors)

    def test_empty_df(self):
        ok, errors = validate_dataframe(pd.DataFrame())
        assert ok is False

    def test_none_df(self):
        ok, errors = validate_dataframe(None)
        assert ok is False

    def test_min_rows_not_met(self):
        df = pd.DataFrame({"a": [1]})
        ok, errors = validate_dataframe(df, min_rows=5)
        assert ok is False


class TestValidatePrice:
    def test_valid_int(self):
        assert validate_price(1000) is True

    def test_valid_float(self):
        assert validate_price(4999.99) is True

    def test_valid_string_number(self):
        assert validate_price("3000") is True

    def test_zero_is_invalid(self):
        assert validate_price(0) is False

    def test_negative_is_invalid(self):
        assert validate_price(-500) is False

    def test_text_is_invalid(self):
        assert validate_price("free") is False

    def test_none_is_invalid(self):
        assert validate_price(None) is False


# ════════════════════════════════════════════════════════════════════════════
# Email automation tests
# ════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def clean_df():
    return pd.DataFrame([
        {
            "hotel_name": "Test Hotel One",
            "category": "Luxury",
            "location": "Mumbai, India",
            "description": "Luxurious stay.",
            "price_inr": 5000.0,
            "rating": 4.5,
            "reviews": 1000,
            "amenities": "WiFi, Pool",
            "availability": "Available",
            "contact_email": "one@testhotel.example.com",
        },
        {
            "hotel_name": "Test Hotel Two",
            "category": "Budget",
            "location": "Delhi, India",
            "description": "Affordable.",
            "price_inr": 1200.0,
            "rating": 3.8,
            "reviews": 200,
            "amenities": "WiFi",
            "availability": "Available",
            "contact_email": "two@testhotel.example.com",
        },
        {
            "hotel_name": "Bad Email Hotel",
            "category": "Resort",
            "location": "Goa, India",
            "description": "By the sea.",
            "price_inr": 6000.0,
            "rating": 4.7,
            "reviews": 500,
            "amenities": "Beach, Pool",
            "availability": "Available",
            "contact_email": "NOT_AN_EMAIL",  # should be skipped
        },
    ])


class TestRenderTemplate:
    def test_basic_render(self):
        template = "Hello {hotel_name} in {location}!"
        record = {"hotel_name": "Grand Hotel", "location": "Mumbai"}
        result = render_template(template, record)
        assert "Grand Hotel" in result
        assert "Mumbai" in result

    def test_missing_field_replaced_with_na(self):
        template = "Price: {price_inr}"
        result = render_template(template, {})
        assert "N/A" in result

    def test_none_value_replaced_with_na(self):
        template = "Category: {category}"
        result = render_template(template, {"category": None})
        assert "N/A" in result

    def test_empty_template(self):
        result = render_template("", {"hotel_name": "Test"})
        assert result == ""


class TestGenerateEmailDrafts:
    def test_returns_list_and_skipped(self, clean_df, tmp_path):
        drafts, skipped = generate_email_drafts(
            clean_df, max_drafts=10,
            export_eml=False,
            output_csv=tmp_path / "drafts.csv",
        )
        assert isinstance(drafts, list)
        assert isinstance(skipped, list)

    def test_invalid_emails_skipped(self, clean_df, tmp_path):
        drafts, skipped = generate_email_drafts(
            clean_df, max_drafts=10,
            export_eml=False,
            output_csv=tmp_path / "drafts.csv",
        )
        # Only 2 valid emails, 1 invalid → 2 drafts, 1 skipped
        assert len(drafts) == 2
        assert len(skipped) >= 1

    def test_draft_fields_present(self, clean_df, tmp_path):
        drafts, _ = generate_email_drafts(
            clean_df, max_drafts=10,
            export_eml=False,
            output_csv=tmp_path / "drafts.csv",
        )
        for draft in drafts:
            assert "draft_id" in draft
            assert "to_email" in draft
            assert "subject" in draft
            assert "body" in draft

    def test_max_drafts_respected(self, clean_df, tmp_path):
        drafts, _ = generate_email_drafts(
            clean_df, max_drafts=1,
            export_eml=False,
            output_csv=tmp_path / "drafts.csv",
        )
        assert len(drafts) <= 1

    def test_empty_dataframe(self, tmp_path):
        drafts, skipped = generate_email_drafts(
            pd.DataFrame(),
            export_eml=False,
            output_csv=tmp_path / "drafts_empty.csv",
        )
        assert drafts == []
        assert len(skipped) >= 1

    def test_csv_exported(self, clean_df, tmp_path):
        output = tmp_path / "drafts.csv"
        drafts, _ = generate_email_drafts(
            clean_df, max_drafts=5,
            export_eml=False,
            output_csv=output,
        )
        if drafts:
            assert output.exists()

    def test_eml_files_created(self, clean_df, tmp_path):
        eml_dir = tmp_path / "eml"
        eml_dir.mkdir()

        import src.email_automation as ea
        original_dir = ea.EML_DIR
        ea.EML_DIR = eml_dir

        try:
            drafts, _ = generate_email_drafts(
                clean_df, max_drafts=2,
                export_eml=True,
                output_csv=tmp_path / "drafts.csv",
            )
        finally:
            ea.EML_DIR = original_dir

        eml_files = list(eml_dir.glob("*.eml"))
        assert len(eml_files) >= 1


class TestPreviewDraft:
    def test_preview_contains_draft_id(self):
        draft = {
            "draft_id": "DRAFT-0001",
            "to_email": "test@example.com",
            "from_email": "sender@example.com",
            "subject": "Test Subject",
            "body": "Hello World",
        }
        preview = preview_draft(draft)
        assert "DRAFT-0001" in preview
        assert "test@example.com" in preview
        assert "Test Subject" in preview
        assert "Hello World" in preview


class TestSendDraftViaSMTP:
    def test_not_sent_without_confirmation(self):
        """send_draft_via_smtp should return False if confirmed=False."""
        draft = {
            "to_email": "test@example.com",
            "subject": "Test",
            "body": "Hello",
        }
        result = send_draft_via_smtp(draft, confirmed=False)
        assert result is False

    def test_not_sent_without_env_vars(self, monkeypatch):
        """Should return False when SMTP env vars are not set."""
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("SMTP_USER", raising=False)
        monkeypatch.delenv("SMTP_PASSWORD", raising=False)
        draft = {
            "to_email": "test@example.com",
            "subject": "Test",
            "body": "Hello",
        }
        result = send_draft_via_smtp(draft, confirmed=True)
        assert result is False
