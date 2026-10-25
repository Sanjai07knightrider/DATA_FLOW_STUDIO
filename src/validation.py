"""
Module 5: Input Validation Utilities
======================================
Shared validation helpers used across modules:
  - Email address format validation
  - Required field checking
  - Dataset size validation
  - Price / numeric range validation
  - Uploaded CSV validation (validate_uploaded_csv, apply_column_fixes)
"""

import re
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# RFC-5322 simplified email pattern — good enough for draft generation
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# ── Schema constants ──────────────────────────────────────────────────────────
REQUIRED_COLUMNS = ["hotel_name"]
OPTIONAL_COLUMNS = [
    "category", "location", "description",
    "price_inr", "rating", "reviews",
    "amenities", "availability", "contact_email",
]
ALL_KNOWN_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

# Hard limits for uploaded files
MAX_UPLOAD_ROWS = 50_000
MAX_UPLOAD_MB   = 20


# ─────────────────────────── Core validators ─────────────────────────────────

def is_valid_email(email: str) -> bool:
    """
    Return True if the email string matches a basic RFC-5322-like pattern.
    Does NOT perform DNS lookup or SMTP verification.

    >>> is_valid_email("user@example.com")
    True
    >>> is_valid_email("not-an-email")
    False
    >>> is_valid_email("")
    False
    """
    if not email or not isinstance(email, str):
        return False
    return bool(_EMAIL_PATTERN.match(email.strip()))


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: Optional[list[str]] = None,
    min_rows: int = 1,
) -> tuple[bool, list[str]]:
    """
    Validate a DataFrame for required columns and minimum row count.

    Returns:
        (is_valid, list_of_error_messages)
    """
    errors = []

    if df is None or df.empty:
        errors.append("DataFrame is empty or None.")
        return False, errors

    if len(df) < min_rows:
        errors.append(f"DataFrame has {len(df)} rows; expected at least {min_rows}.")

    if required_columns:
        missing_cols = [c for c in required_columns if c not in df.columns]
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")

    return len(errors) == 0, errors


def validate_records(records: list[dict]) -> tuple[bool, list[str]]:
    """Check that records is a non-empty list of dicts."""
    errors = []
    if not records:
        errors.append("Records list is empty.")
        return False, errors
    if not isinstance(records[0], dict):
        errors.append("Records must be a list of dicts.")
    return len(errors) == 0, errors


def sanitise_email(email: str) -> str:
    """Return a lowercased, stripped email or empty string if invalid."""
    cleaned = email.strip().lower() if email else ""
    return cleaned if is_valid_email(cleaned) else ""


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


def validate_price(price_value) -> bool:
    """Return True if price_value can be converted to a positive float."""
    try:
        return float(price_value) > 0
    except (TypeError, ValueError):
        return False


# ─────────────────────────── Upload validation ───────────────────────────────

# Alias table: schema_col -> list of recognised alternate column names
_ALIASES: dict[str, list[str]] = {
    "hotel_name":    ["name", "title", "property_name", "hotel", "property", "listing_name"],
    "price_inr":     ["price", "cost", "rate", "tariff", "amount", "nightly_rate"],
    "contact_email": ["email", "mail", "email_address", "contact", "email_id"],
    "rating":        ["stars", "score", "review_score", "avg_rating"],
    "reviews":       ["review_count", "num_reviews", "total_reviews", "reviews_count"],
    "location":      ["city", "place", "address", "region", "area"],
    "category":      ["type", "hotel_type", "property_type", "class"],
    "amenities":     ["facilities", "features", "services"],
    "availability":  ["status", "available", "booking_status"],
    "description":   ["about", "details", "summary", "overview"],
}


def validate_uploaded_csv(
    df: pd.DataFrame,
    filename: str = "",
    size_bytes: int = 0,
) -> dict:
    """
    Validate a user-uploaded CSV DataFrame for use in the pipeline.

    Checks performed:
      - File size within MAX_UPLOAD_MB
      - At least one data row; at most MAX_UPLOAD_ROWS rows
      - Required column `hotel_name` present (or a recognised alias)
      - Which optional columns are present vs missing
      - Extra (unrecognised) columns — allowed but noted
      - All-null columns — warning
      - Duplicate rows — warning

    Returns a dict with keys:
      valid, errors, warnings, info,
      present_cols, missing_cols, extra_cols, alias_map,
      row_count, col_count
    """
    errors: list[str]   = []
    warnings: list[str] = []
    info: list[str]     = []

    # Size limit
    if size_bytes > MAX_UPLOAD_MB * 1024 * 1024:
        errors.append(
            f"File is {size_bytes / 1024 / 1024:.1f} MB — "
            f"exceeds the {MAX_UPLOAD_MB} MB limit."
        )

    # Empty file guard
    if df is None or df.empty:
        errors.append("The uploaded CSV contains no data rows.")
        return _build_result(False, errors, warnings, info, [], [], [], {}, 0, 0)

    row_count = len(df)
    col_count = len(df.columns)

    if row_count > MAX_UPLOAD_ROWS:
        errors.append(
            f"File has {row_count:,} rows — exceeds the "
            f"{MAX_UPLOAD_ROWS:,}-row limit. Upload a smaller sample."
        )

    # Build lookup maps (case-insensitive)
    upload_lower = {c.strip().lower(): c for c in df.columns}   # lower -> actual
    schema_lower = {c.lower(): c for c in ALL_KNOWN_COLUMNS}    # lower -> canonical

    # Exact (case-insensitive) column matching
    present_cols: list[str] = []
    missing_cols: list[str] = []
    col_rename_map: dict[str, str] = {}   # actual -> canonical (for case fixes)

    for s_lower, s_canon in schema_lower.items():
        if s_lower in upload_lower:
            actual = upload_lower[s_lower]
            present_cols.append(s_canon)
            if actual != s_canon:
                col_rename_map[actual] = s_canon  # record case-fix rename
        else:
            missing_cols.append(s_canon)

    # Alias detection for missing schema cols
    alias_map: dict[str, str] = {}   # actual_upload_col -> canonical_schema_col
    claimed_upload_lowers = {c.lower() for c in present_cols}
    remaining_upload = set(upload_lower.keys()) - claimed_upload_lowers

    for schema_col, aliases in _ALIASES.items():
        if schema_col in missing_cols:
            for alias in aliases:
                if alias in remaining_upload:
                    alias_map[upload_lower[alias]] = schema_col
                    remaining_upload.discard(alias)
                    break

    # Extra columns: upload cols not matched to any schema col or alias
    aliased_lowers = {k.lower() for k in alias_map}
    extra_cols = [
        c for c_lower, c in upload_lower.items()
        if c_lower not in schema_lower and c_lower not in aliased_lowers
    ]

    # Required column check
    has_hotel_name_exact = "hotel_name" in present_cols
    has_hotel_name_alias = "hotel_name" in alias_map.values()
    if not has_hotel_name_exact and not has_hotel_name_alias:
        errors.append(
            "Required column `hotel_name` is missing and no recognised alias was found. "
            f"Your columns are: {list(df.columns)}. "
            "Rename a column to `hotel_name` (e.g. 'name', 'title', 'property')."
        )

    # Contact email warning
    has_email_col = (
        "contact_email" in present_cols or "contact_email" in alias_map.values()
    )
    if not has_email_col:
        warnings.append(
            "`contact_email` column not found — email draft generation will be "
            "skipped (no recipient addresses available)."
        )

    # All-null column warnings
    for col in df.columns:
        is_all_null = df[col].isna().all()
        is_all_empty = (df[col].astype(str).str.strip() == "").all()
        if is_all_null or is_all_empty:
            warnings.append(f"Column `{col}` appears to be entirely empty.")

    # Duplicate row warning
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        warnings.append(
            f"{dup_count} duplicate row(s) detected — "
            "they will be removed during cleaning."
        )

    # Info messages
    info.append(f"File: `{filename}` — {row_count:,} rows × {col_count} columns")
    if col_rename_map:
        renames = ", ".join(f"`{k}` → `{v}`" for k, v in col_rename_map.items())
        info.append(f"Column casing auto-corrected: {renames}")
    if alias_map:
        desc = ", ".join(f"`{k}` → `{v}`" for k, v in alias_map.items())
        info.append(f"Column aliases recognised (auto-renamed): {desc}")
    if extra_cols:
        info.append(f"Extra columns preserved as-is: {extra_cols}")

    return _build_result(
        len(errors) == 0,
        errors, warnings, info,
        present_cols, missing_cols, extra_cols, alias_map,
        row_count, col_count,
    )


def _build_result(
    valid: bool,
    errors: list,
    warnings: list,
    info: list,
    present_cols: list,
    missing_cols: list,
    extra_cols: list,
    alias_map: dict,
    row_count: int,
    col_count: int,
) -> dict:
    return {
        "valid":        valid,
        "errors":       errors,
        "warnings":     warnings,
        "info":         info,
        "present_cols": present_cols,
        "missing_cols": missing_cols,
        "extra_cols":   extra_cols,
        "alias_map":    alias_map,
        "row_count":    row_count,
        "col_count":    col_count,
    }


def apply_column_fixes(df: pd.DataFrame, validation_result: dict) -> pd.DataFrame:
    """
    Return a copy of df with column names corrected to canonical schema names:
      - Case-insensitive exact matches are lowercased to the schema name
      - Alias matches are renamed to their canonical schema name

    The original DataFrame is not modified.
    """
    df = df.copy()

    rename_map: dict[str, str] = {}

    # Case-fix renames
    upload_lower = {c.strip().lower(): c for c in df.columns}
    schema_lower = {c.lower(): c for c in ALL_KNOWN_COLUMNS}
    for s_lower, s_canon in schema_lower.items():
        if s_lower in upload_lower:
            actual = upload_lower[s_lower]
            if actual != s_canon:
                rename_map[actual] = s_canon

    # Alias renames (take precedence over any case-fix for the same col)
    rename_map.update(validation_result.get("alias_map", {}))

    if rename_map:
        df.rename(columns=rename_map, inplace=True)
        logger.info("Upload columns renamed: %s", rename_map)

    return df


if __name__ == "__main__":
    test_emails = [
        "valid@example.com",
        "another.user+tag@domain.co.in",
        "bad-email",
        "missing@",
        "@nodomain.com",
        "",
        "spaces in@email.com",
    ]
    for t in test_emails:
        print(f"  {t!r:40s} → {is_valid_email(t)}")
