"""
Tests for Professional Email Draft Export Package
Validates file creation, ZIP contents and directory structure, metadata accuracy,
RFC standards compliance, filename safety, and record-count consistency.
"""

import csv
import email
from email import policy
import json
from pathlib import Path
import zipfile

import pandas as pd
import pytest

from src.email_automation import (
    build_email_draft_package,
    count_eligible_records,
    create_eml_message,
    create_metadata_dict,
    create_text_message,
    generate_email_drafts,
    sanitize_filename,
    sanitize_folder_name,
    compute_folder_names,
    DEFAULT_SUBJECT_TEMPLATE,
    DEFAULT_BODY_TEMPLATE,
)


# ─────────────────────────── Fixtures ────────────────────────────────────────

@pytest.fixture
def sample_clean_df():
    """Cleaned DataFrame with 3 valid records and 1 invalid record."""
    return pd.DataFrame([
        {
            "hotel_id": "HTL-101",
            "hotel_name": "Grand Palace Hotel",
            "category": "Luxury",
            "location": "Mumbai, Maharashtra, India",
            "price_inr": 8500.0,
            "rating": 4.8,
            "reviews": 1250,
            "amenities": "WiFi, Pool, Spa, Gym",
            "availability": "Available",
            "contact_email": "reservations@grandpalace.example.com",
        },
        {
            "hotel_id": "HTL-102",
            "hotel_name": "Seaside Resort & Spa",
            "category": "Resort",
            "location": "Goa, India",
            "price_inr": 6200.0,
            "rating": 4.5,
            "reviews": 840,
            "amenities": "Beach Access, Pool, Bar",
            "availability": "Available",
            "contact_email": "contact@seasideresort.example.com",
        },
        {
            # Missing hotel_id to test deterministic fallback
            "hotel_name": "Budget Inn Central",
            "category": "Budget",
            "location": "Delhi, India",
            "price_inr": 1800.0,
            "rating": 3.9,
            "reviews": 310,
            "amenities": "WiFi, AC",
            "availability": "Available",
            "contact_email": "frontdesk@budgetinn.example.com",
        },
        {
            "hotel_id": "HTL-999",
            "hotel_name": "Invalid Email Hotel",
            "category": "Standard",
            "location": "Pune, India",
            "price_inr": 2500.0,
            "rating": 4.0,
            "reviews": 90,
            "amenities": "WiFi",
            "availability": "Available",
            "contact_email": "invalid-email-address",
        },
    ])


@pytest.fixture
def sample_drafts():
    """Pre-built list of draft dictionaries generated from the same data model."""
    return [
        {
            "draft_id": "DRAFT-0001",
            "recipient": "hotel1@example.com",
            "to_email": "hotel1@example.com",
            "from_email": "Travel Portal Team <noreply@travelportal.example.com>",
            "subject": "Promotional Opportunity for Grand Hotel",
            "body": "Dear Grand Hotel Team,\n\nWe are pleased to introduce our promotional packages.\n\nBest regards,\nTravel Team",
            "hotel_id": "HTL-0001",
            "hotel_name": "Grand Hotel",
            "location": "Mumbai, India",
            "price_inr": 5000.0,
            "rating": 4.5,
            "generation_timestamp": "2026-10-25T12:00:00+00:00",
            "status": "DRAFT",
        },
        {
            "draft_id": "DRAFT-0002",
            "recipient": "hotel2@example.com",
            "to_email": "hotel2@example.com",
            "from_email": "Travel Portal Team <noreply@travelportal.example.com>",
            "subject": "Promotional Opportunity for Coastal Breeze Resort",
            "body": "Dear Coastal Breeze Team,\n\nExplore our latest listing options.\n\nBest regards,\nTravel Team",
            "hotel_id": "HTL-0002",
            "hotel_name": "Coastal Breeze Resort",
            "location": "Goa, India",
            "price_inr": 6500.0,
            "rating": 4.7,
            "generation_timestamp": "2026-10-25T12:00:01+00:00",
            "status": "DRAFT",
        },
    ]


# ─────────────────────────── File Creation Tests ──────────────────────────────

class TestEmailPackageFileCreation:

    def test_creates_draft_folders_and_required_files(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "email_drafts_package"
        zip_path = tmp_path / "email_drafts_export.zip"

        result = build_email_draft_package(sample_drafts, package_dir=pkg_dir, zip_path=zip_path)

        assert Path(result["package_dir"]).exists()
        assert Path(result["zip_path"]).exists()

        # Check each draft folder and its 3 files
        for draft in sample_drafts:
            did = draft["draft_id"]
            draft_folder = pkg_dir / did
            assert draft_folder.is_dir(), f"Folder {did} was not created"

            eml_file = draft_folder / "email.eml"
            txt_file = draft_folder / "email.txt"
            json_file = draft_folder / "metadata.json"

            assert eml_file.is_file(), f"{did}/email.eml is missing"
            assert txt_file.is_file(), f"{did}/email.txt is missing"
            assert json_file.is_file(), f"{did}/metadata.json is missing"

            # Check that files are not empty
            assert eml_file.stat().st_size > 0
            assert txt_file.stat().st_size > 0
            assert json_file.stat().st_size > 0

    def test_creates_root_summary_csv(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "email_drafts_package"
        zip_path = tmp_path / "email_drafts_export.zip"

        build_email_draft_package(sample_drafts, package_dir=pkg_dir, zip_path=zip_path)

        summary_file = pkg_dir / "drafts_summary.csv"
        assert summary_file.is_file()

        with open(summary_file, mode="r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        assert len(rows) == len(sample_drafts)
        expected_cols = {"draft_id", "recipient", "subject", "hotel_id", "hotel_name", "status"}
        assert expected_cols.issubset(set(reader.fieldnames))


# ─────────────────────────── ZIP Contents Tests ───────────────────────────────

class TestZipContentsAndStructure:

    def test_zip_contains_summary_csv_at_root(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "email_drafts_package"
        zip_path = tmp_path / "email_drafts_export.zip"

        build_email_draft_package(sample_drafts, package_dir=pkg_dir, zip_path=zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            assert "drafts_summary.csv" in namelist

    def test_zip_preserves_directory_structure(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "email_drafts_package"
        zip_path = tmp_path / "email_drafts_export.zip"

        build_email_draft_package(sample_drafts, package_dir=pkg_dir, zip_path=zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            for draft in sample_drafts:
                did = draft["draft_id"]
                assert f"{did}/email.eml" in namelist
                assert f"{did}/email.txt" in namelist
                assert f"{did}/metadata.json" in namelist

    def test_zip_files_match_disk_content(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "email_drafts_package"
        zip_path = tmp_path / "email_drafts_export.zip"

        build_email_draft_package(sample_drafts, package_dir=pkg_dir, zip_path=zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            for draft in sample_drafts:
                did = draft["draft_id"]
                zip_json_data = zf.read(f"{did}/metadata.json").decode("utf-8")
                disk_json_data = (pkg_dir / did / "metadata.json").read_text(encoding="utf-8")
                assert json.loads(zip_json_data) == json.loads(disk_json_data)


# ─────────────────────────── Metadata Accuracy Tests ─────────────────────────

class TestMetadataAccuracy:

    def test_metadata_dict_fields_and_values(self, sample_drafts):
        draft = sample_drafts[0]
        meta = create_metadata_dict(draft)

        assert meta["draft_id"] == draft["draft_id"]
        assert meta["recipient"] == draft["recipient"]
        assert meta["subject"] == draft["subject"]
        assert meta["hotel_id"] == draft["hotel_id"]
        assert meta["hotel_name"] == draft["hotel_name"]
        assert meta["location"] == draft["location"]
        assert meta["generation_timestamp"] == draft["generation_timestamp"]
        assert meta["status"] == "DRAFT"

    def test_saved_metadata_json_parseable(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "email_drafts_package"
        zip_path = tmp_path / "email_drafts_export.zip"

        build_email_draft_package(sample_drafts, package_dir=pkg_dir, zip_path=zip_path)

        for draft in sample_drafts:
            json_path = pkg_dir / draft["draft_id"] / "metadata.json"
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)

            assert data["draft_id"] == draft["draft_id"]
            assert data["recipient"] == draft["recipient"]
            assert data["subject"] == draft["subject"]
            assert data["status"] == "DRAFT"
            assert "T" in data["generation_timestamp"]  # ISO timestamp format


# ─────────────────────────── Standards & Formats Tests ───────────────────────

class TestStandardsCompliance:

    def test_eml_rfc2822_compliance(self, sample_drafts):
        draft = sample_drafts[0]
        msg = create_eml_message(draft)
        raw_eml = msg.as_string()

        # Parse with Python standard email library
        parsed = email.message_from_string(raw_eml, policy=policy.default)

        assert parsed["To"] == draft["recipient"]
        assert parsed["Subject"] == draft["subject"]
        assert parsed["From"] is not None
        assert parsed["Date"] is not None
        assert parsed["Message-ID"] is not None
        assert parsed["X-Draft-ID"] == draft["draft_id"]
        assert parsed["X-Status"] == "DRAFT"

        # Verify decoded plain-text body content
        body_part = parsed.get_body(preferencelist=("plain",))
        assert body_part is not None
        assert draft["body"] in body_part.get_content()

    def test_text_message_structure(self, sample_drafts):
        draft = sample_drafts[0]
        txt = create_text_message(draft)

        assert f"To: {draft['recipient']}" in txt
        assert f"Subject: {draft['subject']}" in txt
        assert f"Status: {draft['status']}" in txt
        assert f"Hotel Name: {draft['hotel_name']}" in txt
        assert draft["body"] in txt


# ─────────────────────────── Filename Safety Tests ───────────────────────────

class TestFilenameSafety:

    def test_sanitize_slashes_and_colons(self):
        unsafe = "DRAFT/001:test*hotel?name"
        safe = sanitize_filename(unsafe)
        assert "/" not in safe
        assert "\\" not in safe
        assert ":" not in safe
        assert "*" not in safe
        assert "?" not in safe

    def test_sanitize_empty_and_special(self):
        assert sanitize_filename("") == "draft"
        assert sanitize_filename("   ") == "draft"
        assert sanitize_filename(None) == "draft"

    def test_sanitize_preserves_alphanumeric_and_dashes(self):
        clean = sanitize_filename("DRAFT-0001_A")
        assert clean == "DRAFT-0001_A"

    def test_sanitize_strips_trailing_dots(self):
        assert not sanitize_filename("draft.").endswith(".")


# ─────────────────────────── Record Count Consistency Tests ──────────────────

class TestRecordCountConsistency:

    def test_count_consistency_across_package(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "email_drafts_package"
        zip_path = tmp_path / "email_drafts_export.zip"

        res = build_email_draft_package(sample_drafts, package_dir=pkg_dir, zip_path=zip_path)

        assert res["drafts_count"] == len(sample_drafts)

        # Count folders on disk
        folders = [f for f in pkg_dir.iterdir() if f.is_dir()]
        assert len(folders) == len(sample_drafts)

        # Count rows in summary CSV
        with open(pkg_dir / "drafts_summary.csv", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert len(list(reader)) == len(sample_drafts)

        # Count in ZIP
        with zipfile.ZipFile(zip_path, "r") as zf:
            eml_files_in_zip = [n for n in zf.namelist() if n.endswith("email.eml")]
            assert len(eml_files_in_zip) == len(sample_drafts)

    def test_empty_drafts_list(self, tmp_path):
        pkg_dir = tmp_path / "empty_package"
        zip_path = tmp_path / "empty_export.zip"

        res = build_email_draft_package([], package_dir=pkg_dir, zip_path=zip_path)

        assert res["drafts_count"] == 0
        assert (pkg_dir / "drafts_summary.csv").is_file()
        assert zip_path.is_file()

        with zipfile.ZipFile(zip_path, "r") as zf:
            assert "drafts_summary.csv" in zf.namelist()


# ─────────────────────────── Eligible Records Counting ───────────────────────

class TestEligibleRecordsCounting:

    def test_count_eligible_records_basic(self, sample_clean_df):
        # 3 valid emails, 1 invalid
        eligible = count_eligible_records(sample_clean_df)
        assert eligible == 3

    def test_count_eligible_empty_df(self):
        assert count_eligible_records(pd.DataFrame()) == 0
        assert count_eligible_records(None) == 0
        assert count_eligible_records("not a dataframe") == 0

    def test_count_eligible_no_email_column(self):
        df = pd.DataFrame([{"hotel_name": "Test Hotel", "price": 1000}])
        assert count_eligible_records(df) == 0

    def test_count_eligible_missing_and_nan_values(self):
        df = pd.DataFrame([
            {"contact_email": None},
            {"contact_email": float("nan")},
            {"contact_email": ""},
            {"contact_email": "   "},
            {"contact_email": "valid@example.com"},
        ])
        assert count_eligible_records(df) == 1

    def test_count_eligible_invalid_formats(self):
        df = pd.DataFrame([
            {"contact_email": "plainaddress"},
            {"contact_email": "@missingusername.com"},
            {"contact_email": "username@.com"},
            {"contact_email": "user name@example.com"},
            {"contact_email": "good.email+tag@domain.co.in"},
        ])
        assert count_eligible_records(df) == 1

    def test_count_eligible_fallback_email_col(self):
        df = pd.DataFrame([
            {"email": "hotel1@example.com"},
            {"email": "hotel2@example.com"},
            {"email": "invalid"},
        ])
        assert count_eligible_records(df) == 2

    def test_count_eligible_imported_from_both_modules(self):
        from src.email_automation import count_eligible_records as count_from_email
        from src.validation import count_eligible_records as count_from_validation

        df = pd.DataFrame([{"contact_email": "admin@example.com"}])
        assert count_from_email(df) == 1
        assert count_from_validation(df) == 1


# ─────────────────────────── End-to-End Integration ──────────────────────────

class TestEndToEndPipeline:

    def test_generate_email_drafts_with_export_package(self, sample_clean_df, tmp_path):
        pkg_dir = tmp_path / "package_out"
        zip_path = tmp_path / "archive.zip"
        csv_path = tmp_path / "drafts.csv"

        drafts, skipped = generate_email_drafts(
            sample_clean_df,
            max_drafts=10,
            export_eml=True,
            export_package=True,
            package_dir=pkg_dir,
            zip_path=zip_path,
            output_csv=csv_path,
        )

        # 3 valid records, 1 invalid email skipped
        assert len(drafts) == 3
        assert len(skipped) == 1
        assert "invalid or missing email" in skipped[0]

        # Check export files
        assert csv_path.exists()
        assert zip_path.exists()
        assert (pkg_dir / "drafts_summary.csv").exists()

        # Check individual draft directories
        for draft in drafts:
            did = draft["draft_id"]
            assert (pkg_dir / did / "email.eml").exists()
            assert (pkg_dir / did / "email.txt").exists()
            assert (pkg_dir / did / "metadata.json").exists()

        # Check fallback hotel ID for record without hotel_id
        third_draft = drafts[2]
        assert third_draft["hotel_name"] == "Budget Inn Central"
        assert third_draft["hotel_id"] == "HTL-0003"


# ─────────────────────────── Naming Styles Tests ─────────────────────────────

class TestCustomNamingStyles:

    def test_naming_style_hotel_name(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "hotel_pkg"
        zip_path = tmp_path / "hotel.zip"

        res = build_email_draft_package(
            sample_drafts,
            package_dir=pkg_dir,
            zip_path=zip_path,
            naming_style="Hotel Name",
        )

        assert res["folder_names"] == ["Grand_Hotel", "Coastal_Breeze_Resort"]

        # Check folders on disk
        assert (pkg_dir / "Grand_Hotel" / "email.eml").is_file()
        assert (pkg_dir / "Coastal_Breeze_Resort" / "metadata.json").is_file()

        # Check ZIP structure
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            assert "Grand_Hotel/email.eml" in namelist
            assert "Grand_Hotel/email.txt" in namelist
            assert "Grand_Hotel/metadata.json" in namelist
            assert "Coastal_Breeze_Resort/email.eml" in namelist

        # Check that draft_id is STILL preserved in metadata.json
        meta_json = json.loads((pkg_dir / "Grand_Hotel" / "metadata.json").read_text(encoding="utf-8"))
        assert meta_json["draft_id"] == "DRAFT-0001"
        assert meta_json["folder_name"] == "Grand_Hotel"

    def test_naming_style_recipient_email(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "email_pkg"
        zip_path = tmp_path / "email.zip"

        res = build_email_draft_package(
            sample_drafts,
            package_dir=pkg_dir,
            zip_path=zip_path,
            naming_style="Recipient Email",
        )

        assert res["folder_names"] == ["hotel1_example.com", "hotel2_example.com"]
        assert (pkg_dir / "hotel1_example.com" / "email.txt").is_file()

        with zipfile.ZipFile(zip_path, "r") as zf:
            assert "hotel1_example.com/email.eml" in zf.namelist()

    def test_naming_style_custom_prefix(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "custom_pkg"
        zip_path = tmp_path / "custom.zip"

        res = build_email_draft_package(
            sample_drafts,
            package_dir=pkg_dir,
            zip_path=zip_path,
            naming_style="Custom Prefix + Number",
            custom_prefix="PromoBatch",
        )

        assert res["folder_names"] == ["PromoBatch_0001", "PromoBatch_0002"]
        assert (pkg_dir / "PromoBatch_0001" / "metadata.json").is_file()

        with zipfile.ZipFile(zip_path, "r") as zf:
            assert "PromoBatch_0001/email.eml" in zf.namelist()
            assert "PromoBatch_0002/email.txt" in zf.namelist()

    def test_naming_style_default_is_draft_id(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "default_pkg"
        zip_path = tmp_path / "default.zip"

        res = build_email_draft_package(
            sample_drafts,
            package_dir=pkg_dir,
            zip_path=zip_path,
        )

        assert res["folder_names"] == ["DRAFT-0001", "DRAFT-0002"]
        assert (pkg_dir / "DRAFT-0001" / "email.eml").is_file()


# ─────────────────────────── Collision Prevention Tests ───────────────────────

class TestNamingCollisions:

    def test_duplicate_hotel_names_disambiguated(self, tmp_path):
        drafts = [
            {"draft_id": "DRAFT-0001", "recipient": "a@ex.com", "hotel_name": "The Oberoi", "body": "B1", "subject": "S1"},
            {"draft_id": "DRAFT-0002", "recipient": "b@ex.com", "hotel_name": "The Oberoi", "body": "B2", "subject": "S2"},
            {"draft_id": "DRAFT-0003", "recipient": "c@ex.com", "hotel_name": "The Oberoi", "body": "B3", "subject": "S3"},
        ]
        folder_names = compute_folder_names(drafts, naming_style="Hotel Name")

        assert folder_names == ["The_Oberoi", "The_Oberoi_2", "The_Oberoi_3"]

        pkg_dir = tmp_path / "dup_hotel_pkg"
        zip_path = tmp_path / "dup_hotel.zip"
        build_email_draft_package(drafts, package_dir=pkg_dir, zip_path=zip_path, naming_style="Hotel Name")

        # Verify all 3 folders exist without collision
        for fn in ["The_Oberoi", "The_Oberoi_2", "The_Oberoi_3"]:
            assert (pkg_dir / fn / "email.eml").is_file()

        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            for fn in ["The_Oberoi", "The_Oberoi_2", "The_Oberoi_3"]:
                assert f"{fn}/email.eml" in namelist

    def test_duplicate_email_addresses_disambiguated(self):
        drafts = [
            {"draft_id": "DRAFT-0001", "recipient": "reservations@hotel.com"},
            {"draft_id": "DRAFT-0002", "recipient": "reservations@hotel.com"},
        ]
        folder_names = compute_folder_names(drafts, naming_style="Recipient Email")
        assert folder_names == ["reservations_hotel.com", "reservations_hotel.com_2"]


# ─────────────────────────── Folder Sanitization Tests ────────────────────────

class TestFolderSanitization:

    def test_sanitize_folder_name_forbidden_characters(self):
        unsafe = 'Hotel / Name : * "Test" <VIP> ? | 5-Star'
        safe = sanitize_folder_name(unsafe)

        # None of the illegal characters should be present
        for bad_char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            assert bad_char not in safe

    def test_sanitize_path_traversal(self):
        traversal = "../../etc/passwd"
        safe = sanitize_folder_name(traversal)
        assert "/" not in safe
        assert "\\" not in safe
        assert not safe.startswith(".")

    def test_sanitize_windows_reserved_device_names(self):
        for name in ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]:
            safe = sanitize_folder_name(name)
            assert safe.upper() != name  # e.g. CON_folder

    def test_sanitize_empty_and_spaces(self):
        assert sanitize_folder_name("") == "Folder"
        assert sanitize_folder_name("   ") == "Folder"
        assert sanitize_folder_name(None) == "Folder"

    def test_sanitize_dots_only(self):
        assert sanitize_folder_name("...") == "Folder"
        assert sanitize_folder_name("..") == "Folder"


# ─────────────────── Repackaging Without Regeneration Tests ──────────────────

class TestRepackagingPreservesContent:

    def test_repackaging_keeps_draft_content_identical(self, sample_drafts, tmp_path):
        pkg_dir = tmp_path / "repack_pkg"
        zip_path = tmp_path / "repack.zip"

        # 1. First package with Draft ID
        res1 = build_email_draft_package(
            sample_drafts,
            package_dir=pkg_dir,
            zip_path=zip_path,
            naming_style="Draft ID",
        )
        assert res1["folder_names"] == ["DRAFT-0001", "DRAFT-0002"]

        orig_body = (pkg_dir / "DRAFT-0001" / "email.txt").read_text(encoding="utf-8")

        # 2. Re-package with Hotel Name without regenerating draft content
        res2 = build_email_draft_package(
            sample_drafts,
            package_dir=pkg_dir,
            zip_path=zip_path,
            naming_style="Hotel Name",
        )
        assert res2["folder_names"] == ["Grand_Hotel", "Coastal_Breeze_Resort"]

        # Content in new folder is identical
        new_body = (pkg_dir / "Grand_Hotel" / "email.txt").read_text(encoding="utf-8")
        assert orig_body == new_body

        # Old folder was cleaned
        assert not (pkg_dir / "DRAFT-0001").exists()

