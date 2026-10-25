"""
Module 4: Automated Email Draft Generation
===========================================
Generates personalised email drafts from cleaned dataset records.

Key features:
  - Configurable subject-line and body templates (Jinja2-style {field} syntax).
  - Email address validation before including any recipient.
  - Preview mode to inspect drafts before export.
  - Exports drafts to CSV and individual .eml files.
  - Never sends emails automatically.
  - Optional SMTP integration: only activated via environment variable,
    never by default, and requires explicit user confirmation.
  - Credentials are read from environment variables only — never hardcoded.
"""

import csv
import email.utils
import json
import logging
import os
import re
import shutil
import smtplib
import zipfile
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from string import Formatter
from typing import Optional

import pandas as pd

from .validation import is_valid_email

logger = logging.getLogger(__name__)

__all__ = [
    "generate_email_drafts",
    "preview_draft",
    "render_template",
    "send_draft_via_smtp",
    "count_eligible_records",
    "create_text_message",
    "create_eml_message",
    "create_metadata_dict",
    "sanitize_filename",
    "sanitize_folder_name",
    "compute_folder_names",
    "build_email_draft_package",
    "DEFAULT_SUBJECT_TEMPLATE",
    "DEFAULT_BODY_TEMPLATE",
    "EMAIL_DRAFTS_CSV",
    "EXPORT_ZIP_PATH",
    "SUMMARY_CSV_PATH",
    "ROOT_SUMMARY_CSV",
    "PACKAGE_DIR",
    "EML_DIR",
    "OUTPUT_DIR",
    "SENDER_DISPLAY",
]

# ─────────────────────────── Constants ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
EML_DIR = OUTPUT_DIR / "eml_drafts"
PACKAGE_DIR = OUTPUT_DIR / "email_drafts_package"
EXPORT_ZIP_PATH = OUTPUT_DIR / "email_drafts_export.zip"
SUMMARY_CSV_PATH = PACKAGE_DIR / "drafts_summary.csv"
ROOT_SUMMARY_CSV = OUTPUT_DIR / "drafts_summary.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EML_DIR.mkdir(parents=True, exist_ok=True)
PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

EMAIL_DRAFTS_CSV = OUTPUT_DIR / "email_drafts.csv"

DEFAULT_SUBJECT_TEMPLATE = (
    "Exclusive Offer for {hotel_name} — Limited Availability!"
)

DEFAULT_BODY_TEMPLATE = """\
Dear {hotel_name} Team,

We are pleased to inform you about a special promotional opportunity
for your property listed in our hotel directory.

Property Details:
  Name       : {hotel_name}
  Category   : {category}
  Location   : {location}
  Price/Night: ₹{price_inr}
  Rating     : {rating} ★
  Amenities  : {amenities}

We believe your guests would benefit from our latest travel packages.
Please feel free to reach us at the address below.

Best regards,
The Travel Portal Team
(This is an automated draft — not sent automatically)
"""

SENDER_DISPLAY = "Travel Portal Team <noreply@travelportal.example.com>"


# ─────────────────────────── Template Renderer ───────────────────────────────
def render_template(template: str, record: dict) -> str:
    """
    Safely render a {field} template using record values.
    Missing or NaN fields are replaced with 'N/A' instead of raising errors.
    """
    # Collect all field names referenced in the template
    field_names = [fn for _, fn, _, _ in Formatter().parse(template) if fn]

    safe_record = {}
    for field in field_names:
        value = record.get(field, "N/A")
        if value is None or (isinstance(value, float) and str(value) == "nan"):
            value = "N/A"
        safe_record[field] = str(value).strip()

    try:
        return template.format(**safe_record)
    except KeyError as exc:
        logger.warning("Template field missing: %s", exc)
        return template


# ─────────────────────────── Draft Utilities ─────────────────────────────────
def sanitize_filename(name: str, fallback: str = "draft") -> str:
    """Sanitize draft ID or filename to ensure safe filesystem paths across platforms."""
    if not name:
        return fallback
    clean = re.sub(r"[^\w\-.]", "_", str(name).strip())
    clean = re.sub(r"_+", "_", clean).strip("._")
    return clean if clean else fallback


def sanitize_folder_name(name: str, fallback: str = "Folder", max_length: int = 60) -> str:
    """
    Sanitize folder name for cross-platform filesystem safety (Windows, Linux, macOS).
    Removes invalid characters, path traversal elements, control characters,
    and Windows reserved names.
    """
    if not name or not str(name).strip():
        return fallback

    s = str(name).strip()
    # Replace slashes, backslashes, colons, and illegal filesystem chars: / \ : * ? " < > |
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    # Remove control characters (0-31 and 127)
    s = re.sub(r"[\x00-\x1f\x7f]", "", s)
    # Replace whitespace and repeated punctuation with single underscore
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s)
    # Strip leading/trailing dots and underscores to prevent path traversal (e.g. ".." or ".")
    s = s.strip("._")
    # Truncate length if needed
    if len(s) > max_length:
        s = s[:max_length].rstrip("._")

    # Guard against Windows reserved device names
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if s.upper() in reserved:
        s = f"{s}_folder"

    return s if s else fallback


def compute_folder_names(
    drafts: list[dict],
    naming_style: str = "Draft ID",
    custom_prefix: str = "Draft",
) -> list[str]:
    """
    Generate unique, safe folder names for each draft according to the chosen style.

    Options for naming_style:
      - 'Draft ID': uses draft_id (e.g. DRAFT-0001)
      - 'Hotel Name': uses sanitized hotel_name (e.g. Grand_Palace_Hotel)
      - 'Recipient Email': uses sanitized recipient email (e.g. info_grandhotel_com)
      - 'Custom Prefix + Number': uses prefix entered by user (e.g. Prefix_0001)

    Collisions are resolved by appending numeric suffix (_2, _3, ...).
    All names are sanitized for Windows and POSIX filesystem safety.
    """
    used_lower = set()
    folder_names = []

    style_clean = str(naming_style).lower()

    for idx, draft in enumerate(drafts):
        if "hotel" in style_clean:
            raw = draft.get("hotel_name")
            fallback = f"Hotel_{idx + 1:04d}"
            base = sanitize_folder_name(raw, fallback=fallback)
        elif "recipient" in style_clean or "email" in style_clean:
            raw = draft.get("recipient") or draft.get("to_email", "")
            fallback = f"Email_{idx + 1:04d}"
            if raw:
                raw = str(raw).replace("@", "_")
            base = sanitize_folder_name(raw, fallback=fallback)
        elif "custom" in style_clean or "prefix" in style_clean:
            prefix = sanitize_folder_name(custom_prefix, fallback="Draft")
            base = f"{prefix}_{idx + 1:04d}"
        else:
            # Default to "Draft ID"
            raw = draft.get("draft_id", f"DRAFT-{idx + 1:04d}")
            base = sanitize_folder_name(raw, fallback=f"DRAFT-{idx + 1:04d}")

        # Ensure uniqueness across drafts (case-insensitive for Windows safety)
        candidate = base
        counter = 1
        while candidate.lower() in used_lower:
            counter += 1
            candidate = f"{base}_{counter}"

        used_lower.add(candidate.lower())
        folder_names.append(candidate)

    return folder_names


def count_eligible_records(df: Optional[pd.DataFrame]) -> int:
    """
    Count records in df that possess a valid recipient email address.
    Checks 'contact_email' (or 'email' fallback) using is_valid_email.
    Safely handles None, non-DataFrame objects, empty DataFrames, NaN/missing values.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return 0
    col = "contact_email" if "contact_email" in df.columns else ("email" if "email" in df.columns else None)
    if not col:
        return 0
    return sum(
        1
        for val in df[col]
        if is_valid_email(str(val).strip() if pd.notna(val) else "")
    )


def create_metadata_dict(draft: dict) -> dict:
    """Return the metadata dictionary corresponding to a draft."""
    recipient = draft.get("recipient") or draft.get("to_email", "")
    data = {
        "draft_id": str(draft.get("draft_id", "")),
        "recipient": str(recipient),
        "subject": str(draft.get("subject", "")),
        "hotel_id": str(draft.get("hotel_id", "")),
        "hotel_name": str(draft.get("hotel_name", "N/A")),
        "location": str(draft.get("location", "N/A")),
        "generation_timestamp": str(draft.get("generation_timestamp", "")),
        "status": str(draft.get("status", "DRAFT")),
    }
    if "folder_name" in draft and draft["folder_name"]:
        data["folder_name"] = str(draft["folder_name"])
    return data


def create_text_message(draft: dict) -> str:
    """Return a clean, readable plain-text copy of the draft message."""
    recipient = draft.get("recipient") or draft.get("to_email", "")
    header = (
        f"To: {recipient}\n"
        f"From: {draft.get('from_email', SENDER_DISPLAY)}\n"
        f"Subject: {draft.get('subject', '')}\n"
        f"Date: {draft.get('generation_timestamp', '')}\n"
        f"Status: {draft.get('status', 'DRAFT')}\n"
        f"Hotel ID: {draft.get('hotel_id', 'N/A')}\n"
        f"Hotel Name: {draft.get('hotel_name', 'N/A')}\n"
        f"{'=' * 60}\n\n"
    )
    return header + str(draft.get("body", ""))


def create_eml_message(draft: dict) -> MIMEMultipart:
    """Create a standards-compatible email draft message (RFC 2822)."""
    msg = MIMEMultipart()
    recipient = draft.get("recipient") or draft.get("to_email", "")
    msg["From"] = draft.get("from_email", SENDER_DISPLAY)
    msg["To"] = recipient
    msg["Subject"] = draft.get("subject", "")
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain="travelportal.example.com")
    msg["X-Draft-ID"] = str(draft.get("draft_id", ""))
    msg["X-Status"] = str(draft.get("status", "DRAFT"))
    msg.attach(MIMEText(draft.get("body", ""), "plain", "utf-8"))
    return msg


def build_email_draft_package(
    drafts: list[dict],
    package_dir: Optional[Path] = None,
    zip_path: Optional[Path] = None,
    naming_style: str = "Draft ID",
    custom_prefix: str = "Draft",
) -> dict:
    """
    Build a complete export package containing:
      - A dedicated subfolder per draft named according to `naming_style`:
        - email.eml
        - email.txt
        - metadata.json
      - Root-level drafts_summary.csv
      - email_drafts_export.zip archive preserving directory structure

    Returns a dict with paths and summary information.
    """
    pkg_dir = Path(package_dir) if package_dir else PACKAGE_DIR
    archive_path = Path(zip_path) if zip_path else EXPORT_ZIP_PATH

    pkg_dir.mkdir(parents=True, exist_ok=True)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    # Clean previous draft subdirectories in pkg_dir so switching styles leaves no stale folders
    if pkg_dir.exists():
        for item in pkg_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)

    folder_names = compute_folder_names(drafts, naming_style=naming_style, custom_prefix=custom_prefix)
    summary_rows = []

    for draft, folder_name in zip(drafts, folder_names):
        draft["folder_name"] = folder_name
        draft_folder = pkg_dir / folder_name
        draft_folder.mkdir(parents=True, exist_ok=True)

        # 1. email.eml
        eml_msg = create_eml_message(draft)
        (draft_folder / "email.eml").write_text(eml_msg.as_string(), encoding="utf-8")

        # 2. email.txt
        txt_content = create_text_message(draft)
        (draft_folder / "email.txt").write_text(txt_content, encoding="utf-8")

        # 3. metadata.json
        meta = create_metadata_dict(draft)
        (draft_folder / "metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        summary_rows.append({
            "draft_id": meta["draft_id"],
            "folder_name": folder_name,
            "recipient": meta["recipient"],
            "subject": meta["subject"],
            "hotel_id": meta["hotel_id"],
            "hotel_name": meta["hotel_name"],
            "status": meta["status"],
        })

    # 4. Root drafts_summary.csv in pkg_dir and OUTPUT_DIR
    summary_cols = ["draft_id", "folder_name", "recipient", "subject", "hotel_id", "hotel_name", "status"]
    summary_file = pkg_dir / "drafts_summary.csv"
    with open(summary_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=summary_cols)
        writer.writeheader()
        writer.writerows(summary_rows)

    try:
        root_summary = OUTPUT_DIR / "drafts_summary.csv"
        with open(root_summary, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=summary_cols)
            writer.writeheader()
            writer.writerows(summary_rows)
    except Exception as exc:
        logger.debug("Could not copy root drafts_summary.csv: %s", exc)

    # 5. Build ZIP archive preserving directory structure
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(summary_file, arcname="drafts_summary.csv")
        for draft, folder_name in zip(drafts, folder_names):
            draft_folder = pkg_dir / folder_name
            for fname in ("email.eml", "email.txt", "metadata.json"):
                fpath = draft_folder / fname
                if fpath.exists():
                    zf.write(fpath, arcname=f"{folder_name}/{fname}")

    return {
        "package_dir": str(pkg_dir),
        "zip_path": str(archive_path),
        "zip_size_bytes": archive_path.stat().st_size if archive_path.exists() else 0,
        "drafts_count": len(drafts),
        "summary_csv": str(summary_file),
        "naming_style": naming_style,
        "folder_names": folder_names,
    }


# ─────────────────────────── Draft Generator ─────────────────────────────────
def generate_email_drafts(
    df: pd.DataFrame,
    subject_template: str = DEFAULT_SUBJECT_TEMPLATE,
    body_template: str = DEFAULT_BODY_TEMPLATE,
    sender: str = SENDER_DISPLAY,
    max_drafts: int = 50,
    export_eml: bool = True,
    output_csv: Path = EMAIL_DRAFTS_CSV,
    export_package: bool = True,
    package_dir: Optional[Path] = None,
    zip_path: Optional[Path] = None,
    naming_style: str = "Draft ID",
    custom_prefix: str = "Draft",
) -> tuple[list[dict], list[str]]:
    """
    Generate personalised email drafts for each valid record in df.

    Args:
        df:               Cleaned DataFrame. Recipient email is taken from
                          'contact_email' column.
        subject_template: Subject line template with {field} placeholders.
        body_template:    Message body template with {field} placeholders.
        sender:           Display name / email of the sender.
        max_drafts:       Maximum number of drafts to generate.
        export_eml:       If True, save individual .eml files in output/eml_drafts/.
        output_csv:       Path to the exported drafts CSV.
        export_package:   If True, build DRAFT-XXXX folders and ZIP export package.
        package_dir:      Custom directory for the export package.
        zip_path:         Custom path for the email_drafts_export.zip archive.
        naming_style:     Folder naming style ('Draft ID', 'Hotel Name',
                          'Recipient Email', 'Custom Prefix + Number').
        custom_prefix:    Prefix used when naming_style is 'Custom Prefix + Number'.

    Returns:
        (drafts_list, skipped_reasons)
        drafts_list:     List of draft dicts.
        skipped_reasons: Human-readable notes on skipped records.
    """
    if df is None or df.empty:
        logger.warning("No data provided for email generation.")
        if export_package:
            build_email_draft_package(
                [],
                package_dir=package_dir,
                zip_path=zip_path,
                naming_style=naming_style,
                custom_prefix=custom_prefix,
            )
        return [], ["DataFrame is empty"]

    drafts = []
    skipped = []
    count = 0

    for idx, row in df.iterrows():
        if count >= max_drafts:
            skipped.append(f"Stopped at max_drafts limit ({max_drafts}).")
            break

        record = row.to_dict()

        # ── Validate recipient email ──────────────────────────────────────────
        raw_recipient = record.get("contact_email")
        recipient = str(raw_recipient).strip() if pd.notna(raw_recipient) else ""
        if not is_valid_email(recipient):
            reason = f"Row {idx}: invalid or missing email '{recipient}' — skipped."
            logger.warning(reason)
            skipped.append(reason)
            continue

        # ── Determine hotel ID ────────────────────────────────────────────────
        raw_hotel_id = (
            record.get("hotel_id")
            or record.get("id")
            or record.get("property_id")
            or record.get("hotel_code")
        )
        if raw_hotel_id is not None and str(raw_hotel_id).strip() and str(raw_hotel_id).lower() != "nan":
            hotel_id = str(raw_hotel_id).strip()
        else:
            hotel_id = f"HTL-{count + 1:04d}"

        # ── Render subject and body ──────────────────────────────────────────
        subject = render_template(subject_template, record)
        body = render_template(body_template, record)
        timestamp = datetime.now(timezone.utc).isoformat()

        hotel_name = str(record.get("hotel_name", "N/A"))
        if not hotel_name or hotel_name == "nan":
            hotel_name = "N/A"

        location = str(record.get("location", "N/A"))
        if not location or location == "nan":
            location = "N/A"

        draft_id = f"DRAFT-{count + 1:04d}"

        draft = {
            "draft_id": draft_id,
            "recipient": recipient,
            "to_email": recipient,  # legacy alias
            "from_email": sender,
            "subject": subject,
            "body": body,
            "hotel_id": hotel_id,
            "hotel_name": hotel_name,
            "location": location,
            "price_inr": record.get("price_inr", "N/A"),
            "rating": record.get("rating", "N/A"),
            "generation_timestamp": timestamp,
            "status": "DRAFT",
        }
        drafts.append(draft)

        # ── Export individual legacy .eml file ────────────────────────────────
        if export_eml:
            _save_eml(draft, EML_DIR)

        count += 1

    # ── Export all drafts to CSV ──────────────────────────────────────────────
    if drafts:
        _save_drafts_csv(drafts, output_csv)
        logger.info("Generated %d email drafts → %s", len(drafts), output_csv)
    else:
        logger.warning("No valid drafts generated.")

    # ── Export professional package & zip ─────────────────────────────────────
    if export_package:
        build_email_draft_package(
            drafts,
            package_dir=package_dir,
            zip_path=zip_path,
            naming_style=naming_style,
            custom_prefix=custom_prefix,
        )

    return drafts, skipped


def _save_eml(draft: dict, eml_dir: Path) -> None:
    """Save a single draft dict as a .eml (RFC 2822 format) file."""
    msg = MIMEMultipart()
    msg["From"] = draft["from_email"]
    msg["To"] = draft["to_email"]
    msg["Subject"] = draft["subject"]
    msg.attach(MIMEText(draft["body"], "plain", "utf-8"))

    # Use draft_id as filename
    safe_id = re.sub(r"[^\w\-]", "_", draft["draft_id"])
    eml_path = eml_dir / f"{safe_id}.eml"
    eml_path.write_text(msg.as_string(), encoding="utf-8")
    logger.debug("Saved .eml: %s", eml_path)


def _save_drafts_csv(drafts: list[dict], output_path: Path) -> None:
    """Save all drafts to a CSV file."""
    if not drafts:
        return
    fieldnames = list(drafts[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(drafts)


# ─────────────────────────── Preview Helper ──────────────────────────────────
def preview_draft(draft: dict) -> str:
    """Return a formatted text preview of a single email draft."""
    sep = "─" * 60
    recipient = draft.get("to_email") or draft.get("recipient", "")
    return (
        f"{sep}\n"
        f"Draft ID : {draft.get('draft_id')}\n"
        f"To       : {recipient}\n"
        f"From     : {draft.get('from_email')}\n"
        f"Subject  : {draft.get('subject')}\n"
        f"{sep}\n"
        f"{draft.get('body', '')}\n"
        f"{sep}"
    )


# ─────────────────────────── Optional SMTP Send ──────────────────────────────
def send_draft_via_smtp(
    draft: dict,
    confirmed: bool = False,
) -> bool:
    """
    Optionally send a single draft via SMTP.

    SAFETY RULES:
      1. 'confirmed' MUST be explicitly True — never auto-send.
      2. SMTP credentials are read from environment variables ONLY.
      3. If any credential is missing, sending is aborted.

    Environment variables required:
      SMTP_HOST     — e.g. smtp.gmail.com
      SMTP_PORT     — e.g. 587
      SMTP_USER     — sender email address
      SMTP_PASSWORD — app password (never a plain account password)

    Returns True if sent successfully, False otherwise.
    """
    if not confirmed:
        logger.info("SMTP send skipped — user confirmation required.")
        return False

    host = os.environ.get("SMTP_HOST", "")
    port_str = os.environ.get("SMTP_PORT", "587")
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")

    if not all([host, user, password]):
        logger.error(
            "SMTP not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, "
            "SMTP_PASSWORD environment variables."
        )
        return False

    try:
        port = int(port_str)
        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = draft["to_email"]
        msg["Subject"] = draft["subject"]
        msg.attach(MIMEText(draft["body"], "plain", "utf-8"))

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
            server.sendmail(user, [draft["to_email"]], msg.as_string())

        logger.info("Email sent to: %s", draft["to_email"])
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("SMTP send failed: %s", exc)
        return False


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from data_collection import load_fallback_csv
    from data_cleaning import clean_data

    raw = load_fallback_csv()
    df_clean, _ = clean_data(raw)
    drafts, skipped = generate_email_drafts(df_clean, max_drafts=3)
    for d in drafts:
        print(preview_draft(d))
    if skipped:
        print("Skipped:", skipped)
