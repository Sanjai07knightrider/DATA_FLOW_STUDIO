"""
Module 2: Data Cleaning and Preparation
========================================
Cleans raw collected data using Pandas:
  - Identifies and handles missing values
  - Removes duplicate records
  - Normalises whitespace and text fields
  - Converts columns to appropriate data types
  - Validates required fields
  - Reports dimensions before and after cleaning
  - Exports cleaned dataset to CSV
  - Preserves raw data separately
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

# ─────────────────────────── Logging ────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─────────────────────────── Constants ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLEANED_OUTPUT_CSV = OUTPUT_DIR / "cleaned_data.csv"
REQUIRED_FIELDS = ["hotel_name", "category", "price_inr"]


# ─────────────────────────── Core Cleaning Function ─────────────────────────
def clean_data(
    records: list[dict],
    output_path: Path = CLEANED_OUTPUT_CSV,
) -> tuple[pd.DataFrame, dict]:
    """
    Clean a list of record dicts and return the cleaned DataFrame plus a
    summary report dictionary.

    Args:
        records:     Raw records from the collection module.
        output_path: Where to save the cleaned CSV.

    Returns:
        (cleaned_df, summary_dict)
    """
    if not records:
        logger.warning("clean_data received empty records list.")
        empty_df = pd.DataFrame()
        return empty_df, {"error": "No records supplied"}

    # ── Step 1: Load into DataFrame ──────────────────────────────────────────
    df = pd.DataFrame(records)
    raw_rows, raw_cols = df.shape
    logger.info("Raw dataset: %d rows × %d columns", raw_rows, raw_cols)

    # ── Step 2: Track missing values before cleaning ─────────────────────────
    missing_before = df.isnull().sum().to_dict()
    empty_before = {col: (df[col].astype(str).str.strip() == "").sum()
                    for col in df.columns}

    # ── Step 3: Replace empty strings with NaN ───────────────────────────────
    df.replace("", pd.NA, inplace=True)

    # ── Step 4: Normalise whitespace in text columns ─────────────────────────
    text_cols = ["hotel_name", "category", "location", "description",
                 "amenities", "availability", "contact_email"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace(
                r"\s+", " ", regex=True
            )
            df[col] = df[col].replace("nan", pd.NA)  # fix str(NaN)

    # ── Step 5: Type conversions ─────────────────────────────────────────────
    if "price_inr" in df.columns:
        df["price_inr"] = pd.to_numeric(
            df["price_inr"].astype(str).str.replace(r"[^0-9.]", "", regex=True),
            errors="coerce",
        )

    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(
            df["rating"].astype(str).str.replace(r"[^0-9.]", "", regex=True),
            errors="coerce",
        )

    if "reviews" in df.columns:
        df["reviews"] = pd.to_numeric(
            df["reviews"].astype(str).str.replace(r"[^0-9]", "", regex=True),
            errors="coerce",
        ).astype("Int64")

    # ── Step 6: Remove duplicates ─────────────────────────────────────────────
    duplicates_removed = df.duplicated().sum()
    df.drop_duplicates(inplace=True)
    logger.info("Duplicates removed: %d", duplicates_removed)

    # ── Step 7: Validate required fields — drop rows where all required missing
    before_validation = len(df)
    df["_has_required"] = df[
        [f for f in REQUIRED_FIELDS if f in df.columns]
    ].notna().any(axis=1)
    invalid_rows = len(df[~df["_has_required"]])
    df = df[df["_has_required"]].drop(columns=["_has_required"])
    logger.info("Rows dropped (failed required-field check): %d", invalid_rows)

    # ── Step 8: Fill remaining NaNs with sensible defaults ───────────────────
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("N/A")

    # ── Step 9: Reset index ───────────────────────────────────────────────────
    df.reset_index(drop=True, inplace=True)
    clean_rows, clean_cols = df.shape
    logger.info("Cleaned dataset: %d rows × %d columns", clean_rows, clean_cols)

    # ── Step 10: Export ───────────────────────────────────────────────────────
    df.to_csv(output_path, index=False)
    logger.info("Cleaned data saved to: %s", output_path)

    # ── Build Summary ─────────────────────────────────────────────────────────
    missing_after = df.isnull().sum().to_dict()
    summary = {
        "raw_rows": raw_rows,
        "raw_cols": raw_cols,
        "cleaned_rows": clean_rows,
        "cleaned_cols": clean_cols,
        "duplicates_removed": int(duplicates_removed),
        "invalid_rows_dropped": invalid_rows,
        "rows_removed_total": raw_rows - clean_rows,
        "missing_values_before": {k: int(v) for k, v in missing_before.items()},
        "empty_strings_before": {k: int(v) for k, v in empty_before.items()},
        "missing_values_after": {k: int(v) for k, v in missing_after.items()},
        "output_path": str(output_path),
    }
    return df, summary


def load_cleaned_csv(path: Path = CLEANED_OUTPUT_CSV) -> Optional[pd.DataFrame]:
    """Load previously saved cleaned CSV, or return None if not found."""
    if not path.exists():
        logger.warning("Cleaned CSV not found at: %s", path)
        return None
    df = pd.read_csv(path, dtype=str)
    # Re-apply numeric conversions
    for col in ("price_inr", "rating"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "reviews" in df.columns:
        df["reviews"] = pd.to_numeric(df["reviews"], errors="coerce").astype("Int64")
    return df


def get_cleaning_report(df: pd.DataFrame, summary: dict) -> str:
    """Return a human-readable text report of the cleaning process."""
    lines = [
        "=" * 55,
        "         DATA CLEANING REPORT",
        "=" * 55,
        f"  Raw rows:          {summary.get('raw_rows', 'N/A')}",
        f"  Raw columns:       {summary.get('raw_cols', 'N/A')}",
        f"  Cleaned rows:      {summary.get('cleaned_rows', 'N/A')}",
        f"  Cleaned columns:   {summary.get('cleaned_cols', 'N/A')}",
        f"  Duplicates removed:{summary.get('duplicates_removed', 0)}",
        f"  Invalid rows dropped:{summary.get('invalid_rows_dropped', 0)}",
        f"  Total rows removed:{summary.get('rows_removed_total', 0)}",
        "-" * 55,
        "  Missing values after cleaning:",
    ]
    for col, count in summary.get("missing_values_after", {}).items():
        if count > 0:
            lines.append(f"    {col}: {count} missing")
    lines.append("=" * 55)
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick standalone test using the fallback CSV
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from data_collection import load_fallback_csv

    raw = load_fallback_csv()
    df_clean, report = clean_data(raw)
    print(get_cleaning_report(df_clean, report))
    print(df_clean.head())
