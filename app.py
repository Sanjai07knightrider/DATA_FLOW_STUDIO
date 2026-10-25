"""
app.py — Main Streamlit Dashboard
===================================
DataFlow Studio — Web Data Collection & Automated Email Generation System
Internship Project — Training Trains Software Technologies & Institute / DomainHostly.com

Run with:  streamlit run app.py
"""

import io
import json
import sys
import time
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

# ─────────────────────────── Path Setup ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.data_collection import (
    collect_data,
    load_fallback_csv,
    parse_local_html,
    RAW_OUTPUT_CSV,
)
from src.data_cleaning import (
    clean_data,
    get_cleaning_report,
    load_cleaned_csv,
    CLEANED_OUTPUT_CSV,
)
from src.synthetic_data import (
    generate_synthetic_data,
    get_synthetic_summary,
    SYNTHETIC_OUTPUT_CSV,
)
from src.email_automation import (
    generate_email_drafts,
    preview_draft,
    count_eligible_records,
    create_text_message,
    create_eml_message,
    create_metadata_dict,
    sanitize_filename,
    sanitize_folder_name,
    compute_folder_names,
    build_email_draft_package,
    DEFAULT_SUBJECT_TEMPLATE,
    DEFAULT_BODY_TEMPLATE,
    EMAIL_DRAFTS_CSV,
    EXPORT_ZIP_PATH,
    SUMMARY_CSV_PATH,
    PACKAGE_DIR,
)
from src.validation import (
    validate_uploaded_csv,
    apply_column_fixes,
)

OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─────────────────────────── Page Configuration ──────────────────────────────
st.set_page_config(
    page_title="DataFlow Studio — Data Collection & Email Automation",
    page_icon="❖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────── Design System & CSS ─────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

  /* Typography Base */
  html, body, p, h1, h2, h3, h4, h5, h6, input, button, select, textarea, label {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #F4F4F5;
  }

  code, pre, .stCodeBlock, .stCodeBlock * {
    font-family: 'JetBrains Mono', monospace !important;
  }

  /* Protect Material Symbols from font overrides */
  .material-icons,
  .material-symbols-rounded,
  .material-symbols-outlined,
  [data-testid="stIconMaterial"],
  [data-testid*="stIcon"] {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
  }

  /* Main background (#101114) */
  .stApp {
    background-color: #101114 !important;
  }

  /* ── Sidebar System (#15161A, width: ~260–280px) ────────────────────────── */
  [data-testid="stSidebarHeader"] {
    display: none !important;
    height: 0 !important;
    padding: 0 !important;
  }
  [data-testid="stSidebarCollapseButton"] {
    display: none !important;
  }

  [data-testid="stSidebar"] {
    min-width: 265px !important;
    max-width: 280px !important;
    width: 275px !important;
    background-color: #15161A !important;
    border-right: 1px solid #2C2E35 !important;
    overflow-x: hidden !important;
  }
  [data-testid="stSidebar"] > div:first-child {
    padding: 1.25rem 1rem !important;
    overflow-x: hidden !important;
  }

  /* Brand Header */
  .sidebar-brand-box {
    padding: 0.25rem 0.25rem 1.15rem 0.25rem;
    border-bottom: 1px solid #2C2E35;
    margin-bottom: 1.15rem;
  }
  .sidebar-brand-title {
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #F4F4F5;
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  .sidebar-brand-title svg.brand-logo {
    flex-shrink: 0;
  }
  .sidebar-brand-subtitle {
    font-size: 0.72rem;
    color: #A1A1AA;
    margin-top: 0.25rem;
    font-weight: 500;
    letter-spacing: 0.01em;
  }

  /* Navigation Radio Group */
  div[data-testid="stRadio"] > div {
    gap: 0.25rem !important;
  }
  div[data-testid="stRadio"] > div > label {
    display: flex !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    padding: 0.45rem 0.75rem !important;
    border-radius: 6px !important;
    margin: 0 !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    border-left: 3px solid transparent !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
  }
  div[data-testid="stRadio"] > div > label:hover {
    background: #24262D !important;
  }
  div[data-testid="stRadio"] > div > label:hover p {
    color: #F4F4F5 !important;
  }

  /* Active Navigation Style: Refined charcoal surface, indigo text & thin indigo indicator */
  div[data-testid="stRadio"] > div > label:has(input:checked) {
    background: #24262D !important;
    border-color: #383A44 !important;
    border-left: 3px solid #6366F1 !important;
    border-radius: 0 6px 6px 0 !important;
  }
  div[data-testid="stRadio"] > div > label:has(input:checked) p {
    color: #F4F4F5 !important;
    font-weight: 600 !important;
  }
  div[data-testid="stRadio"] > div > label p {
    color: #A1A1AA !important;
    font-size: 0.86rem !important;
    font-weight: 500 !important;
    margin: 0 !important;
    display: flex !important;
    align-items: center !important;
  }

  /* Hide default radio circle completely */
  div[data-testid="stRadio"] input[type="radio"],
  div[data-testid="stRadio"] div[data-testid="stRadioButton"] {
    display: none !important;
  }

  /* Section Header Injection */
  div[data-testid="stRadio"] > div > label:nth-child(1)::before {
    content: "WORKSPACE";
    width: 100% !important;
    flex-basis: 100% !important;
    display: block;
    font-size: 0.65rem;
    font-weight: 700;
    color: #71717A;
    letter-spacing: 0.08em;
    margin-bottom: 0.45rem;
    padding-left: 0.2rem;
  }
  div[data-testid="stRadio"] > div > label:nth-child(5)::before {
    content: "AUTOMATION";
    width: 100% !important;
    flex-basis: 100% !important;
    display: block;
    font-size: 0.65rem;
    font-weight: 700;
    color: #71717A;
    letter-spacing: 0.08em;
    margin-top: 1.25rem;
    margin-bottom: 0.45rem;
    padding-top: 0.85rem;
    padding-left: 0.2rem;
    border-top: 1px solid #2C2E35;
  }
  div[data-testid="stRadio"] > div > label:nth-child(7)::before {
    content: "RESOURCES";
    width: 100% !important;
    flex-basis: 100% !important;
    display: block;
    font-size: 0.65rem;
    font-weight: 700;
    color: #71717A;
    letter-spacing: 0.08em;
    margin-top: 1.25rem;
    margin-bottom: 0.45rem;
    padding-top: 0.85rem;
    padding-left: 0.2rem;
    border-top: 1px solid #2C2E35;
  }

  /* Lucide-Style Monochrome Line Icons via CSS Data URIs */
  div[data-testid="stRadio"] > div > label p::before {
    content: "";
    display: inline-block;
    width: 16px;
    height: 16px;
    margin-right: 9px;
    vertical-align: -2.5px;
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    flex-shrink: 0;
    transition: all 0.15s ease;
  }

  /* 1. Overview (Dashboard Grid) */
  div[data-testid="stRadio"] > div > label:nth-child(1) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23A1A1AA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='7' height='9' x='3' y='3' rx='1'/%3E%3Crect width='7' height='5' x='14' y='3' rx='1'/%3E%3Crect width='7' height='9' x='14' y='12' rx='1'/%3E%3Crect width='7' height='5' x='3' y='16' rx='1'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(1):hover p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23F4F4F5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='7' height='9' x='3' y='3' rx='1'/%3E%3Crect width='7' height='5' x='14' y='3' rx='1'/%3E%3Crect width='7' height='9' x='14' y='12' rx='1'/%3E%3Crect width='7' height='5' x='3' y='16' rx='1'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(1):has(input:checked) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23818CF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='7' height='9' x='3' y='3' rx='1'/%3E%3Crect width='7' height='5' x='14' y='3' rx='1'/%3E%3Crect width='7' height='9' x='14' y='12' rx='1'/%3E%3Crect width='7' height='5' x='3' y='16' rx='1'/%3E%3C/svg%3E");
  }

  /* 2. Data Collection (Download/Ingest) */
  div[data-testid="stRadio"] > div > label:nth-child(2) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23A1A1AA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/%3E%3Cpolyline points='7 10 12 15 17 10'/%3E%3Cline x1='12' x2='12' y1='15' y2='3'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(2):hover p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23F4F4F5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/%3E%3Cpolyline points='7 10 12 15 17 10'/%3E%3Cline x1='12' x2='12' y1='15' y2='3'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(2):has(input:checked) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23818CF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/%3E%3Cpolyline points='7 10 12 15 17 10'/%3E%3Cline x1='12' x2='12' y1='15' y2='3'/%3E%3C/svg%3E");
  }

  /* 3. Raw Dataset (Table) */
  div[data-testid="stRadio"] > div > label:nth-child(3) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23A1A1AA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3v18'/%3E%3Crect width='18' height='18' x='3' y='3' rx='2'/%3E%3Cpath d='M3 9h18'/%3E%3Cpath d='M3 15h18'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(3):hover p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23F4F4F5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3v18'/%3E%3Crect width='18' height='18' x='3' y='3' rx='2'/%3E%3Cpath d='M3 9h18'/%3E%3Cpath d='M3 15h18'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(3):has(input:checked) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23818CF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3v18'/%3E%3Crect width='18' height='18' x='3' y='3' rx='2'/%3E%3Cpath d='M3 9h18'/%3E%3Cpath d='M3 15h18'/%3E%3C/svg%3E");
  }

  /* 4. Data Cleaning (Sparkles) */
  div[data-testid="stRadio"] > div > label:nth-child(4) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23A1A1AA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(4):hover p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23F4F4F5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(4):has(input:checked) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23818CF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z'/%3E%3C/svg%3E");
  }

  /* 5. Synthetic Data (Cpu/Model) */
  div[data-testid="stRadio"] > div > label:nth-child(5) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23A1A1AA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='16' height='16' x='4' y='4' rx='2'/%3E%3Crect width='6' height='6' x='9' y='9' rx='1'/%3E%3Cpath d='M15 2v2'/%3E%3Cpath d='M15 20v2'/%3E%3Cpath d='M2 15h2'/%3E%3Cpath d='M2 9h2'/%3E%3Cpath d='M20 15h2'/%3E%3Cpath d='M20 9h2'/%3E%3Cpath d='M9 2v2'/%3E%3Cpath d='M9 20v2'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(5):hover p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23F4F4F5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='16' height='16' x='4' y='4' rx='2'/%3E%3Crect width='6' height='6' x='9' y='9' rx='1'/%3E%3Cpath d='M15 2v2'/%3E%3Cpath d='M15 20v2'/%3E%3Cpath d='M2 15h2'/%3E%3Cpath d='M2 9h2'/%3E%3Cpath d='M20 15h2'/%3E%3Cpath d='M20 9h2'/%3E%3Cpath d='M9 2v2'/%3E%3Cpath d='M9 20v2'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(5):has(input:checked) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23818CF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='16' height='16' x='4' y='4' rx='2'/%3E%3Crect width='6' height='6' x='9' y='9' rx='1'/%3E%3Cpath d='M15 2v2'/%3E%3Cpath d='M15 20v2'/%3E%3Cpath d='M2 15h2'/%3E%3Cpath d='M2 9h2'/%3E%3Cpath d='M20 15h2'/%3E%3Cpath d='M20 9h2'/%3E%3Cpath d='M9 2v2'/%3E%3Cpath d='M9 20v2'/%3E%3C/svg%3E");
  }

  /* 6. Email Drafts (Mail) */
  div[data-testid="stRadio"] > div > label:nth-child(6) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23A1A1AA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='20' height='16' x='2' y='4' rx='2'/%3E%3Cpath d='m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(6):hover p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23F4F4F5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='20' height='16' x='2' y='4' rx='2'/%3E%3Cpath d='m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(6):has(input:checked) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23818CF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect width='20' height='16' x='2' y='4' rx='2'/%3E%3Cpath d='m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7'/%3E%3C/svg%3E");
  }

  /* 7. Download Reports (Archive/Package) */
  div[data-testid="stRadio"] > div > label:nth-child(7) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23A1A1AA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z'/%3E%3Cpath d='m3.3 7 8.7 5 8.7-5'/%3E%3Cpath d='M12 22V12'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(7):hover p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23F4F4F5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z'/%3E%3Cpath d='m3.3 7 8.7 5 8.7-5'/%3E%3Cpath d='M12 22V12'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(7):has(input:checked) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23818CF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z'/%3E%3Cpath d='m3.3 7 8.7 5 8.7-5'/%3E%3Cpath d='M12 22V12'/%3E%3C/svg%3E");
  }

  /* 8. Project Info (Info) */
  div[data-testid="stRadio"] > div > label:nth-child(8) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23A1A1AA' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3Cpath d='M12 16v-4'/%3E%3Cpath d='M12 8h.01'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(8):hover p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23F4F4F5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3Cpath d='M12 16v-4'/%3E%3Cpath d='M12 8h.01'/%3E%3C/svg%3E");
  }
  div[data-testid="stRadio"] > div > label:nth-child(8):has(input:checked) p::before {
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23818CF8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3Cpath d='M12 16v-4'/%3E%3Cpath d='M12 8h.01'/%3E%3C/svg%3E");
  }

  /* Sidebar Bottom Safety Panel */
  .sidebar-footer-box {
    background: #1B1D22;
    border: 1px solid #2C2E35;
    border-radius: 8px;
    padding: 0.85rem;
    margin-top: 1.5rem;
  }
  .sidebar-footer-tag {
    font-size: 0.68rem;
    font-weight: 700;
    color: #F4F4F5;
    display: flex;
    align-items: center;
    gap: 0.45rem;
    letter-spacing: 0.05em;
  }
  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #4ADE80;
    box-shadow: 0 0 6px rgba(74, 222, 128, 0.45);
    display: inline-block;
    flex-shrink: 0;
  }
  .sidebar-footer-desc {
    font-size: 0.72rem;
    color: #A1A1AA;
    margin-top: 0.35rem;
    line-height: 1.4;
  }

  /* ── Page Header Component ────────────────────────────────────────────── */
  .page-header {
    margin-bottom: 1.5rem;
    padding-bottom: 0.95rem;
    border-bottom: 1px solid #2C2E35;
  }
  .page-top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.45rem;
  }
  .page-step-badge {
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #818CF8;
    background: rgba(129, 140, 248, 0.1);
    border: 1px solid rgba(129, 140, 248, 0.25);
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
  }
  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.72rem;
    color: #A1A1AA;
    background: #1B1D22;
    border: 1px solid #2C2E35;
    padding: 0.2rem 0.65rem;
    border-radius: 9999px;
  }
  .page-title {
    font-size: 1.55rem;
    font-weight: 700;
    color: #F4F4F5;
    letter-spacing: -0.02em;
    margin: 0 0 0.25rem 0;
  }
  .page-description {
    font-size: 0.88rem;
    color: #A1A1AA;
    margin: 0;
    line-height: 1.45;
  }

  /* ── Callout Banners ──────────────────────────────────────────────────── */
  .callout-box {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    border-radius: 8px;
    padding: 0.85rem 1.15rem;
    margin-bottom: 1.25rem;
  }
  .callout-box.safety {
    background: #1B1D22;
    border: 1px solid #2C2E35;
  }
  .callout-box.safety .callout-icon { color: #4ADE80; font-size: 1.1rem; }
  .callout-box.safety .callout-text { color: #E4E4E7; font-size: 0.84rem; line-height: 1.45; }
  .callout-box.safety strong { color: #F4F4F5; }

  .callout-box.info {
    background: #1B1D22;
    border: 1px solid #2C2E35;
  }
  .callout-box.info .callout-icon { color: #818CF8; font-size: 1.1rem; }
  .callout-box.info .callout-text { color: #A1A1AA; font-size: 0.84rem; line-height: 1.45; }
  .callout-box.info strong { color: #F4F4F5; }

  /* ── UI Card Surface (#1B1D22) ────────────────────────────────────────── */
  .ui-card {
    background: #1B1D22;
    border: 1px solid #2C2E35;
    border-radius: 8px;
    padding: 1.15rem;
    margin-bottom: 1rem;
  }
  .ui-card-title {
    font-size: 0.9rem;
    font-weight: 700;
    color: #F4F4F5;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  /* ── Horizontal Stepper Component ─────────────────────────────────────── */
  .stepper-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
  }
  .stepper-item {
    flex: 1 1 180px;
    min-width: 160px;
    background: #1B1D22;
    border: 1px solid #2C2E35;
    border-radius: 8px;
    padding: 0.85rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    transition: all 0.15s ease;
  }
  .stepper-item.completed {
    border-color: rgba(74, 222, 128, 0.35);
    background: rgba(74, 222, 128, 0.04);
  }
  .stepper-item.active {
    border-color: rgba(99, 102, 241, 0.45);
    background: rgba(99, 102, 241, 0.08);
  }
  .stepper-item.pending {
    border-color: #24262D;
    background: #15161A;
    opacity: 0.65;
  }
  .stepper-badge {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    flex-shrink: 0;
  }
  .stepper-item.completed .stepper-badge { background: #4ADE80; color: #101114; }
  .stepper-item.active .stepper-badge { background: #6366F1; color: #FFFFFF; }
  .stepper-item.pending .stepper-badge { background: #24262D; color: #71717A; }
  .stepper-title { font-size: 0.82rem; font-weight: 700; color: #F4F4F5; }
  .stepper-subtitle { font-size: 0.7rem; color: #A1A1AA; margin-top: 0.1rem; }

  /* ── Metric Card Styling (#1B1D22 with #2C2E35 border) ─────────────────── */
  [data-testid="stMetric"] {
    background: #1B1D22 !important;
    border: 1px solid #2C2E35 !important;
    border-radius: 8px !important;
    padding: 0.85rem 1.15rem !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25) !important;
  }
  [data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: #A1A1AA !important;
  }
  [data-testid="stMetricValue"] {
    font-size: 1.65rem !important;
    font-weight: 700 !important;
    color: #F4F4F5 !important;
    letter-spacing: -0.02em !important;
  }
  [data-testid="stMetricDelta"] svg {
    fill: #818CF8 !important;
  }
  [data-testid="stMetricDelta"] div {
    color: #818CF8 !important;
    font-weight: 600 !important;
  }

  /* ── Expander Overlap Fixes ────────────────────────────────────────────── */
  [data-testid="stExpander"] {
    border: 1px solid #2C2E35 !important;
    border-radius: 8px !important;
    background: #1B1D22 !important;
    margin-bottom: 0.85rem !important;
    overflow: visible !important;
  }
  [data-testid="stExpander"] summary {
    padding: 0.75rem 1rem !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    color: #F4F4F5 !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.65rem !important;
    cursor: pointer !important;
  }
  [data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"] {
    flex-shrink: 0 !important;
    width: 1.25rem !important;
    height: 1.25rem !important;
    color: #A1A1AA !important;
  }
  [data-testid="stExpander"] summary p {
    margin: 0 !important;
    line-height: 1.4 !important;
  }
  [data-testid="stExpanderDetails"] {
    padding: 1rem !important;
    border-top: 1px solid #2C2E35 !important;
  }

  /* ── Buttons (Soft Indigo Primary, Dark Charcoal Secondary) ───────────── */
  button[kind="primary"],
  button[data-testid="stBaseButton-primary"] {
    background: #6366F1 !important;
    border: none !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    transition: all 0.15s ease !important;
  }
  button[kind="primary"]:hover,
  button[data-testid="stBaseButton-primary"]:hover {
    background: #4F46E5 !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3) !important;
  }
  button[kind="secondary"],
  button[data-testid="stBaseButton-secondary"] {
    background: #1B1D22 !important;
    border: 1px solid #2C2E35 !important;
    color: #F4F4F5 !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    transition: all 0.15s ease !important;
  }
  button[kind="secondary"]:hover,
  button[data-testid="stBaseButton-secondary"]:hover {
    background: #24262D !important;
    border-color: #3F424E !important;
  }

  /* Form Elements */
  input, select, textarea, div[data-baseweb="select"] > div {
    background-color: #15161A !important;
    border-color: #2C2E35 !important;
    color: #F4F4F5 !important;
    border-radius: 6px !important;
  }
  input:focus, textarea:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 1px #6366F1 !important;
  }

  /* ── Tabs ─────────────────────────────────────────────────────────────── */
  .stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    border-bottom: 1px solid #2C2E35;
  }
  .stTabs [data-baseweb="tab"] {
    padding: 0.5rem 0.9rem;
    font-weight: 600;
    font-size: 0.86rem;
    color: #A1A1AA;
  }
  .stTabs [aria-selected="true"] {
    color: #F4F4F5 !important;
    border-bottom-color: #6366F1 !important;
  }

  /* ── File Catalog Layout (Download Reports) ────────────────────────────── */
  .badge-neutral {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: #24262D;
    color: #A1A1AA;
    border: 1px solid #2C2E35;
    padding: 0.12rem 0.45rem;
    border-radius: 4px;
  }
  .badge-primary-archive {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: rgba(99, 102, 241, 0.15);
    color: #818CF8;
    border: 1px solid rgba(99, 102, 241, 0.35);
    padding: 0.12rem 0.45rem;
    border-radius: 4px;
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────── Helper Functions ────────────────────────────────
def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Encode DataFrame to CSV bytes safely in UTF-8."""
    return df.to_csv(index=False).encode("utf-8")


def file_to_bytes(path: Path) -> bytes:
    """Read binary bytes from a disk file."""
    if path.exists():
        return path.read_bytes()
    return b""


# ─────────────────────────── Session State Initialisation ────────────────────
for key in (
    "raw_records",
    "raw_df",
    "clean_df",
    "clean_summary",
    "syn_df",
    "email_drafts",
    "email_skipped",
    "upload_source",
    "upload_validation_result",
    "uploaded_original_df",
):
    if key not in st.session_state:
        st.session_state[key] = None


# ═════════════════════════════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION
# ═════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand-box">
        <div class="sidebar-brand-title">
            <svg class="brand-logo" width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="8" height="8" rx="2" fill="#6366F1" />
                <rect x="13" y="3" width="8" height="8" rx="2" fill="#24262D" stroke="#2C2E35" stroke-width="1.5" />
                <rect x="3" y="13" width="8" height="8" rx="2" fill="#24262D" stroke="#2C2E35" stroke-width="1.5" />
                <rect x="13" y="13" width="8" height="8" rx="2" fill="#818CF8" fill-opacity="0.25" stroke="#818CF8" stroke-width="1.5" />
            </svg>
            <span>DataFlow Studio</span>
        </div>
        <div class="sidebar-brand-subtitle">Data Collection &amp; Email Automation</div>
    </div>
    """, unsafe_allow_html=True)

    page_options = [
        "Overview",
        "Data Collection",
        "Raw Dataset",
        "Data Cleaning",
        "Synthetic Data",
        "Email Drafts",
        "Download Reports",
        "Project Info",
    ]

    page = st.radio(
        "Navigation",
        page_options,
        label_visibility="collapsed",
    )

    st.markdown("""
    <div class="sidebar-footer-box">
        <div class="sidebar-footer-tag">
            <span class="status-dot"></span> LOCAL-ONLY WORKSPACE
        </div>
        <div class="sidebar-footer-desc">
            Data processing and email draft generation remain local. Emails are never sent automatically.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE: OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
if page in ("Overview", "Project Overview"):
    st.markdown("""
    <div class="page-header">
        <div class="page-top-bar">
            <span class="page-step-badge">Data Science Dashboard</span>
            <div class="status-pill">
                <span class="status-dot"></span> System Active · Localhost:8501
            </div>
        </div>
        <h1 class="page-title">Project Overview</h1>
        <p class="page-description">An end-to-end data pipeline demonstrating ethical web data collection, schema enforcement, data preparation, synthetic benchmark generation, and automated email draft packaging.</p>
    </div>
    """, unsafe_allow_html=True)

    # Actual state metrics
    has_raw = st.session_state.raw_df is not None and not st.session_state.raw_df.empty
    has_clean = st.session_state.clean_df is not None and not st.session_state.clean_df.empty
    has_syn = st.session_state.syn_df is not None and not st.session_state.syn_df.empty
    has_drafts = st.session_state.email_drafts is not None and len(st.session_state.email_drafts) > 0

    raw_count = len(st.session_state.raw_df) if has_raw else 0
    clean_count = len(st.session_state.clean_df) if has_clean else 0
    syn_count = len(st.session_state.syn_df) if has_syn else 0
    draft_count = len(st.session_state.email_drafts) if has_drafts else 0

    # 4 Equal-width KPI Cards
    st.markdown("#### Pipeline Key Metrics")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Raw Records", f"{raw_count:,}" if has_raw else "0", delta="Collected" if has_raw else "Empty")
    with kpi2:
        st.metric("Cleaned Records", f"{clean_count:,}" if has_clean else "0", delta="Ready" if has_clean else "Pending")
    with kpi3:
        st.metric("Synthetic Records", f"{syn_count:,}" if has_syn else "0", delta="Generated" if has_syn else "None")
    with kpi4:
        st.metric("Email Drafts", f"{draft_count:,}" if has_drafts else "0", delta="Packaged" if has_drafts else "None")

    # Pipeline Stepper
    st.markdown("#### Pipeline Progression")
    s1_cls = "completed" if has_raw else "active"
    s2_cls = "completed" if has_clean else ("active" if has_raw else "pending")
    s3_cls = "completed" if has_syn else ("active" if has_clean else "pending")
    s4_cls = "completed" if has_drafts else ("active" if has_clean else "pending")
    s5_cls = "completed" if (has_drafts and EXPORT_ZIP_PATH.exists()) else ("active" if has_drafts else "pending")

    s1_badge = "✓" if has_raw else "1"
    s2_badge = "✓" if has_clean else "2"
    s3_badge = "✓" if has_syn else "3"
    s4_badge = "✓" if has_drafts else "4"
    s5_badge = "✓" if (has_drafts and EXPORT_ZIP_PATH.exists()) else "5"

    st.markdown(f"""
    <div class="stepper-container">
        <div class="stepper-item {s1_cls}">
            <div class="stepper-badge">{s1_badge}</div>
            <div class="stepper-body">
                <div class="stepper-title">Collection</div>
                <div class="stepper-subtitle">{'Done · ' + str(raw_count) + ' rows' if has_raw else 'Ready to ingest'}</div>
            </div>
        </div>
        <div class="stepper-item {s2_cls}">
            <div class="stepper-badge">{s2_badge}</div>
            <div class="stepper-body">
                <div class="stepper-title">Cleaning</div>
                <div class="stepper-subtitle">{'Done · ' + str(clean_count) + ' rows' if has_clean else 'Pending step 1'}</div>
            </div>
        </div>
        <div class="stepper-item {s3_cls}">
            <div class="stepper-badge">{s3_badge}</div>
            <div class="stepper-body">
                <div class="stepper-title">Synthetic Data</div>
                <div class="stepper-subtitle">{'Done · ' + str(syn_count) + ' rows' if has_syn else 'Optional benchmark'}</div>
            </div>
        </div>
        <div class="stepper-item {s4_cls}">
            <div class="stepper-badge">{s4_badge}</div>
            <div class="stepper-body">
                <div class="stepper-title">Email Drafts</div>
                <div class="stepper-subtitle">{'Done · ' + str(draft_count) + ' drafts' if has_drafts else 'Pending step 2'}</div>
            </div>
        </div>
        <div class="stepper-item {s5_cls}">
            <div class="stepper-badge">{s5_badge}</div>
            <div class="stepper-body">
                <div class="stepper-title">Export Package</div>
                <div class="stepper-subtitle">{'ZIP archive ready' if (has_drafts and EXPORT_ZIP_PATH.exists()) else 'Pending drafts'}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not has_raw:
        st.markdown("""
        <div class="callout-box info">
            <div class="callout-icon">ℹ</div>
            <div class="callout-text">
                <strong>No dataset ingested yet</strong>: Go to <strong>Data Collection</strong> in the sidebar to load the bundled sample hotel data or upload your custom CSV file.
            </div>
        </div>
        """, unsafe_allow_html=True)

    col_obj, col_doc = st.columns(2)
    with col_obj:
        st.markdown("""
        <div class="ui-card">
            <div class="ui-card-title">Core System Capabilities</div>
            <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.85rem; color: #A1A1AA; line-height: 1.8;">
                <li>Reliable HTML &amp; CSV ingestion with resilient fallback options</li>
                <li>Audit-traceable data preparation, normalization, and deduplication</li>
                <li>Reproducible synthetic generation using controlled random seeds</li>
                <li>Safe, local email draft packaging with individual EML, TXT, and JSON files</li>
                <li>Exportable ZIP packages with customizable folder naming schemes</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_doc:
        st.markdown("""
        <div class="ui-card">
            <div class="ui-card-title">Documented Internship Modules</div>
            <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.85rem; color: #A1A1AA; line-height: 1.8;">
                <li><strong>Module 1:</strong> Web Data Collection &amp; Parser (<code>data_collection.py</code>)</li>
                <li><strong>Module 2:</strong> Data Preparation &amp; Audit Pipeline (<code>data_cleaning.py</code>)</li>
                <li><strong>Module 3:</strong> Synthetic Benchmark Engine (<code>synthetic_data.py</code>)</li>
                <li><strong>Module 4:</strong> Automated Email Draft Generator (<code>email_automation.py</code>)</li>
                <li><strong>Module 5:</strong> Schema Validation &amp; Normalization (<code>validation.py</code>)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE: DATA COLLECTION
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Data Collection":
    st.markdown("""
    <div class="page-header">
        <div class="page-top-bar">
            <span class="page-step-badge">Step 1 of 4</span>
            <div class="status-pill">
                <span class="status-dot"></span> Ingestion Engine
            </div>
        </div>
        <h1 class="page-title">Data Collection</h1>
        <p class="page-description">Acquire hotel listing datasets via permitted public web targets, bundled offline sample data, or custom CSV file uploads.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_builtin, tab_upload = st.tabs(["Built-in Sources", "Upload Custom CSV"])

    # ── Tab 1: Built-in Sources ──────────────────────────────────────────────
    with tab_builtin:
        col1, col2 = st.columns([3, 1])
        with col1:
            source = st.selectbox(
                "Select Data Source",
                ["local", "fallback", "online"],
                format_func=lambda x: {
                    "local":    "Local HTML Document (data/sample_page.html) — Deterministic Offline Demo",
                    "fallback": "Pre-bundled CSV Dataset (data/sample_data.csv) — Static Offline Fallback",
                    "online":   "Public Web Target (books.toscrape.com) — Permitted Live Web Source",
                }[x],
            )
        with col2:
            st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
            collect_btn = st.button("▶ Collect Data", type="primary", use_container_width=True)

        if source == "online":
            st.info("Connecting to `books.toscrape.com` with educational user-agent headers and polite rate limiting. No login or CAPTCHA restrictions are bypassed.")

        if collect_btn:
            with st.spinner(f"Collecting records from {source}…"):
                records = collect_data(source)

            if records:
                st.session_state.raw_records  = records
                st.session_state.raw_df        = pd.DataFrame(records)
                st.session_state.upload_source = source
                st.session_state.clean_df      = None
                st.session_state.clean_summary = None
                st.session_state.syn_df        = None
                st.session_state.email_drafts  = None
                st.session_state.email_skipped = None
                st.success(f"Successfully collected **{len(records)}** records from `{source}`.")
            else:
                st.error("Failed to collect records from source. Please try an offline fallback.")

        if st.session_state.raw_df is not None and st.session_state.upload_source != "csv_upload":
            st.markdown("#### Ingested Records Preview")
            df = st.session_state.raw_df
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingested Records", len(df))
            m2.metric("Schema Columns", len(df.columns))
            m3.metric("Active Source", str(st.session_state.upload_source).upper())
            st.dataframe(df.head(10), use_container_width=True)

        with st.expander("Ethical Scraping Standards Applied"):
            st.markdown("""
            - **Transparent Identification**: Educational bot User-Agent string passed with HTTP requests.
            - **Rate Limiting**: Intentional sleep delays applied between consecutive page requests.
            - **No Circumvention**: Operates strictly within public endpoints without authentication or session spoofing.
            - **High Reliability**: Bundled offline datasets ensure zero reliance on live network connections during demos.
            """)

    # ── Tab 2: CSV Upload ─────────────────────────────────────────────────────
    with tab_upload:
        st.markdown("Upload your custom `.csv` dataset. The schema validator inspects columns, normalizes alias names (e.g. `name` → `hotel_name`, `email` → `contact_email`), and feeds the cleaning pipeline.")

        uploaded_file = st.file_uploader(
            "Select CSV file",
            type=["csv"],
            help="Maximum 20 MB · Up to 50,000 rows",
            key="csv_file_uploader",
        )

        if uploaded_file is not None:
            filename = uploaded_file.name
            file_bytes = uploaded_file.getvalue()
            size_bytes = len(file_bytes)

            try:
                raw_upload_df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    dtype=str,
                    keep_default_na=False,
                )
            except Exception as parse_err:
                st.error(f"Failed to parse `{filename}`: {parse_err}. Ensure file is valid UTF-8 CSV.")
                st.stop()

            # Metadata Overview
            st.markdown("#### Upload Metrics")
            uc1, uc2, uc3, uc4 = st.columns(4)
            uc1.metric("File Name", filename[:20] + "…" if len(filename) > 22 else filename)
            uc2.metric("Total Rows", f"{len(raw_upload_df):,}")
            uc3.metric("Detected Columns", len(raw_upload_df.columns))
            uc4.metric("File Size", f"{size_bytes / 1024:.1f} KB")

            # Validation
            vr = validate_uploaded_csv(raw_upload_df, filename=filename, size_bytes=size_bytes)
            st.session_state.upload_validation_result = vr

            if vr["errors"]:
                for err in vr["errors"]:
                    st.error(err)

            if vr["warnings"]:
                for warn in vr["warnings"]:
                    st.warning(warn)

            if vr["info"]:
                for msg in vr["info"]:
                    st.info(msg)

            with st.expander("Column Compatibility Audit", expanded=True):
                col_rows = []
                for col in [
                    "hotel_name", "category", "location", "description",
                    "price_inr", "rating", "reviews", "amenities",
                    "availability", "contact_email",
                ]:
                    if col in vr["present_cols"]:
                        status = "Exact Match"
                        note = "Standard schema column"
                    elif col in vr["alias_map"].values():
                        matched_alias = next(k for k, v in vr["alias_map"].items() if v == col)
                        status = "Alias Detected"
                        note = f"Maps `{matched_alias}` → `{col}`"
                    else:
                        status = "Optional Missing"
                        note = "Filled with 'N/A' during cleaning"
                    col_rows.append({
                        "Target Column": f"{col} {'⭐ (Required)' if col == 'hotel_name' else ''}",
                        "Status": status,
                        "Resolution": note,
                    })
                if vr["extra_cols"]:
                    for ex in vr["extra_cols"]:
                        col_rows.append({
                            "Target Column": ex,
                            "Status": "Additional Column",
                            "Resolution": "Preserved in dataset",
                        })
                st.dataframe(pd.DataFrame(col_rows), use_container_width=True, hide_index=True)

            st.markdown("#### Ingestion Sample (First 10 Rows)")
            st.dataframe(raw_upload_df.head(10), use_container_width=True)

            if vr["valid"]:
                fixed_df = apply_column_fixes(raw_upload_df, vr)
                safe_stem = Path(filename).stem.replace(" ", "_")[:40]
                original_save_path = OUTPUT_DIR / f"uploaded_original_{safe_stem}.csv"
                fixed_df.to_csv(original_save_path, index=False)
                st.session_state.uploaded_original_df = fixed_df.copy()

                if st.button("▶ Ingest Dataset into Pipeline", type="primary", key="use_uploaded_btn"):
                    records = fixed_df.to_dict(orient="records")
                    st.session_state.raw_records  = records
                    st.session_state.raw_df        = fixed_df.copy()
                    st.session_state.upload_source = "csv_upload"
                    for stale_key in ("clean_df", "clean_summary", "syn_df", "email_drafts", "email_skipped"):
                        st.session_state[stale_key] = None

                    st.success(f"Ingested **{len(records)}** records into the pipeline. Navigate to **Data Cleaning** to proceed.")
                    st.caption(f"Original file preserved at: `output/{original_save_path.name}`")
            else:
                st.error("This file cannot be ingested until the blocking validation errors above are resolved.")

        else:
            st.markdown("#### Recommended CSV Format")
            schema_guide = pd.DataFrame([
                {"Column": "hotel_name",    "Requirement": "Required (or alias)", "Example": "The Grand Palace Hotel"},
                {"Column": "category",      "Requirement": "Optional",            "Example": "Luxury / Resort"},
                {"Column": "location",      "Requirement": "Optional",            "Example": "Mumbai, India"},
                {"Column": "price_inr",     "Requirement": "Optional",            "Example": "5000"},
                {"Column": "rating",        "Requirement": "Optional",            "Example": "4.5"},
                {"Column": "contact_email", "Requirement": "Required for Drafts", "Example": "reservations@hotel.com"},
            ])
            st.dataframe(schema_guide, use_container_width=True, hide_index=True)

            template_df = pd.DataFrame([{
                "hotel_name": "Example Grand Hotel",
                "category": "Luxury",
                "location": "Mumbai, India",
                "price_inr": "5000",
                "rating": "4.5",
                "reviews": "1200",
                "amenities": "WiFi, Pool, Spa",
                "availability": "Available",
                "contact_email": "reservations@example.com",
            }])
            st.download_button(
                "⬇ Download Template CSV",
                data=df_to_csv_bytes(template_df),
                file_name="hotel_dataset_template.csv",
                mime="text/csv",
                key="download_template_csv",
            )


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE: RAW DATASET
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Raw Dataset":
    st.markdown("""
    <div class="page-header">
        <div class="page-top-bar">
            <span class="page-step-badge">Data Inspection</span>
            <div class="status-pill">
                <span class="status-dot"></span> Pre-Cleaning View
            </div>
        </div>
        <h1 class="page-title">Raw Dataset Preview</h1>
        <p class="page-description">Inspect ingested raw hotel records, data type distributions, and missing value indicators prior to cleaning.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.raw_df is None:
        st.warning("No dataset collected yet. Ingest data via Data Collection first.")
        if st.button("Load Sample Hotel Dataset Now"):
            records = load_fallback_csv()
            st.session_state.raw_records = records
            st.session_state.raw_df = pd.DataFrame(records)
            st.rerun()
    else:
        df = st.session_state.raw_df
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ingested Rows", f"{len(df):,}")
        c2.metric("Total Schema Columns", len(df.columns))
        c3.metric("Raw Missing Values", int(df.isnull().sum().sum()))

        st.markdown("#### Ingested Records Table")
        st.dataframe(df, use_container_width=True, height=380)

        with st.expander("Schema Health & Data Type Diagnostics"):
            info_data = {
                "Column Name": df.columns.tolist(),
                "Non-Null Count": df.notna().sum().tolist(),
                "Null Count": df.isnull().sum().tolist(),
                "Detected Type": [str(df[c].dtype) for c in df.columns],
                "Sample Entry": [str(df[c].iloc[0]) if len(df) > 0 else "" for c in df.columns],
            }
            st.dataframe(pd.DataFrame(info_data), use_container_width=True)

        st.download_button(
            "⬇ Export Raw Data CSV",
            data=df_to_csv_bytes(df),
            file_name="raw_collected_data.csv",
            mime="text/csv",
        )


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE: DATA CLEANING
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Data Cleaning":
    st.markdown("""
    <div class="page-header">
        <div class="page-top-bar">
            <span class="page-step-badge">Step 2 of 4</span>
            <div class="status-pill">
                <span class="status-dot"></span> Pipeline Stage 2
            </div>
        </div>
        <h1 class="page-title">Data Cleaning &amp; Preparation</h1>
        <p class="page-description">Execute automated data hygiene: strip whitespace, remove duplicates, convert numeric values, and audit missing fields.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.raw_records is None:
        st.warning("Ingest a dataset in Data Collection before running data cleaning.")
        if st.button("Load Sample Dataset"):
            records = load_fallback_csv()
            st.session_state.raw_records = records
            st.session_state.raw_df = pd.DataFrame(records)
            st.rerun()
    else:
        col_op1, col_op2 = st.columns(2)
        with col_op1:
            st.markdown("""
            <div class="ui-card">
                <div class="ui-card-title">Text Normalization &amp; Deduplication</div>
                <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.85rem; color: #A1A1AA; line-height: 1.7;">
                    <li>Normalize whitespace across text and location columns</li>
                    <li>Eliminate identical duplicate rows across all fields</li>
                    <li>Convert empty strings and blank tokens to formal NaN</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with col_op2:
            st.markdown("""
            <div class="ui-card">
                <div class="ui-card-title">Schema Coercion &amp; Validation</div>
                <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.85rem; color: #A1A1AA; line-height: 1.7;">
                    <li>Coerce price, ratings, and reviews to appropriate numeric types</li>
                    <li>Verify presence of non-empty primary identifier fields</li>
                    <li>Impute unpopulated optional fields with clean <code>N/A</code> fallbacks</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        if st.button("▶ Run Data Cleaning", type="primary"):
            with st.spinner("Cleaning raw dataset…"):
                df_clean, summary = clean_data(
                    st.session_state.raw_records,
                    output_path=CLEANED_OUTPUT_CSV,
                )
            st.session_state.clean_df = df_clean
            st.session_state.clean_summary = summary
            st.session_state.syn_df = None
            st.session_state.email_drafts = None
            st.session_state.email_skipped = None
            st.success("Data cleaning pipeline executed successfully.")

        if st.session_state.clean_df is not None:
            df = st.session_state.clean_df
            summary = st.session_state.clean_summary or {}

            st.markdown("#### Preparation Audit Results")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Raw Rows", summary.get("raw_rows", len(df)))
            c2.metric("Cleaned Rows", summary.get("cleaned_rows", len(df)))
            c3.metric("Duplicates Dropped", summary.get("duplicates_removed", 0))
            c4.metric("Total Rows Dropped", summary.get("rows_removed_total", 0))

            st.markdown("#### Cleaned Dataset")
            st.dataframe(df, use_container_width=True, height=350)

            with st.expander("Complete Cleaning Audit Log"):
                report = get_cleaning_report(df, summary)
                st.code(report, language=None)

            with st.expander("Missing Values Post-Cleaning"):
                mv = summary.get("missing_values_after", {})
                mv_df = pd.DataFrame(list(mv.items()), columns=["Field Name", "Missing Count"])
                st.dataframe(mv_df, use_container_width=True)

            st.download_button(
                "⬇ Download Cleaned Data CSV",
                data=df_to_csv_bytes(df),
                file_name="cleaned_data.csv",
                mime="text/csv",
            )


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE: SYNTHETIC DATA
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Synthetic Data":
    st.markdown("""
    <div class="page-header">
        <div class="page-top-bar">
            <span class="page-step-badge">Step 3 of 4</span>
            <div class="status-pill">
                <span class="status-dot"></span> Statistical Benchmark
            </div>
        </div>
        <h1 class="page-title">Synthetic Data Generation</h1>
        <p class="page-description">Generate statistically realistic benchmark records for model training and pipeline testing without exposing sensitive data.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="callout-box info">
        <div class="callout-icon">ℹ</div>
        <div class="callout-text">
            <strong>Synthetic Data Engine</strong>: All records generated below are machine-synthesized benchmarks.
            They mirror the schema and distributions of the cleaned dataset but contain <strong>no genuine personally identifiable information</strong>.
            All synthetic rows are tagged with <span style="background: rgba(129, 140, 248, 0.15); color: #818CF8; padding: 0.1rem 0.4rem; border-radius: 4px; font-weight: 600;">record_type = SYNTHETIC</span>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.clean_df is None:
        st.warning("Cleaned dataset required. Please run Data Cleaning first.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            n_records = st.slider("Record Volume to Synthesize", 5, 200, 20, 5)
        with col2:
            seed = st.number_input("Random Seed (Reproducibility)", min_value=0, max_value=9999, value=42)

        if st.button("▶ Generate Synthetic Data", type="primary"):
            with st.spinner("Synthesizing records…"):
                syn_df = generate_synthetic_data(
                    st.session_state.clean_df,
                    n_records=n_records,
                    seed=int(seed),
                    output_path=SYNTHETIC_OUTPUT_CSV,
                )
            st.session_state.syn_df = syn_df
            st.success(f"Generated **{len(syn_df)}** synthetic benchmark records (seed={seed}).")

        if st.session_state.syn_df is not None:
            df = st.session_state.syn_df
            summary = get_synthetic_summary(df)

            st.markdown("#### Synthetic Benchmark Metrics")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Generated Count", summary.get("total_records", 0))
            c2.metric("Min Tariff (₹)", f"₹{summary.get('price_min', 0):,}")
            c3.metric("Max Tariff (₹)", f"₹{summary.get('price_max', 0):,}")
            c4.metric("Mean Rating", summary.get("rating_mean", "—"))

            st.markdown("#### Synthetic Dataset Table")
            st.dataframe(df, use_container_width=True, height=350)

            with st.expander("Synthetic Category Distribution"):
                cat_counts = df["category"].value_counts().reset_index()
                cat_counts.columns = ["Category", "Record Count"]
                st.dataframe(cat_counts, use_container_width=True)

            st.download_button(
                "⬇ Download Synthetic Data CSV",
                data=df_to_csv_bytes(df),
                file_name="synthetic_data.csv",
                mime="text/csv",
            )


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE: EMAIL DRAFTS
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Email Drafts":
    st.markdown("""
    <div class="page-header">
        <div class="page-top-bar">
            <span class="page-step-badge">Step 4 of 4 · Export Package Engine</span>
            <div class="status-pill">
                <span class="status-dot"></span> Local Sandbox Safe
            </div>
        </div>
        <h1 class="page-title">Automated Email Draft Generation</h1>
        <p class="page-description">Construct personalized, standards-compliant email drafts from your cleaned dataset and package them into structured folders.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="callout-box safety">
        <div class="callout-icon">🔒</div>
        <div class="callout-text">
            <strong>Local-Only Safety Guarantee</strong>: Email drafts are strictly generated as local files on disk.
            No live emails are dispatched automatically. Each draft includes standard RFC-2822 <code>email.eml</code>, plain text <code>email.txt</code>, and complete <code>metadata.json</code>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.clean_df is None:
        st.warning("No cleaned dataset available. Please ingest data and run Data Cleaning first.")
        st.info("The email generation module exclusively operates on your currently active cleaned dataset to ensure strict data integrity.")
    else:
        df_clean = st.session_state.clean_df
        eligible_count = count_eligible_records(df_clean)
        total_clean = len(df_clean)

        st.info(f"Target Dataset: Current Cleaned Dataset — **{total_clean} records** ({eligible_count} eligible with valid contact email).")

        if eligible_count == 0:
            st.warning("None of the rows in the current cleaned dataset have valid contact email addresses. Ingest a dataset with valid recipient emails in `contact_email` to generate drafts.")

        # Configuration Panel
        with st.expander("Email Template Configuration", expanded=False):
            subject_tpl = st.text_input("Subject Template", value=DEFAULT_SUBJECT_TEMPLATE)
            body_tpl = st.text_area("Body Template", value=DEFAULT_BODY_TEMPLATE, height=220)
            st.caption("Available template variables: `{hotel_name}`, `{category}`, `{location}`, `{price_inr}`, `{rating}`, `{amenities}`")

        # Draft parameters
        c_param1, c_param2 = st.columns(2)
        with c_param1:
            default_max = min(20, max(eligible_count, 1))
            slider_max = max(10, min(200, max(eligible_count, 50)))
            max_drafts = st.slider("Draft Generation Volume", 1, slider_max, default_max)
        with c_param2:
            export_eml = st.checkbox("Export individual .eml files to output/eml_drafts/", value=True)

        # ── Draft Folder Naming Style ─────────────────────────────────────────
        st.markdown("#### Draft Folder Naming Style")
        naming_col, prefix_col = st.columns([2, 1])
        with naming_col:
            naming_style_choice = st.selectbox(
                "Draft Folder Naming Style",
                options=[
                    "Draft ID: DRAFT-0001",
                    "Hotel Name: sanitized hotel name",
                    "Recipient Email: sanitized recipient email",
                    "Custom Prefix + Number: user enters a prefix, producing Prefix_0001, Prefix_0002, etc.",
                ],
                index=0,
                key="naming_style_select",
                help="Configure how individual draft folders are named inside the ZIP archive and export directory.",
            )

        if "Hotel Name" in naming_style_choice:
            selected_style = "Hotel Name"
        elif "Recipient Email" in naming_style_choice:
            selected_style = "Recipient Email"
        elif "Custom Prefix" in naming_style_choice:
            selected_style = "Custom Prefix + Number"
        else:
            selected_style = "Draft ID"

        custom_prefix_val = "Draft"
        with prefix_col:
            if selected_style == "Custom Prefix + Number":
                custom_prefix_val = st.text_input(
                    "Custom Folder Prefix",
                    value="Draft",
                    max_chars=25,
                    key="custom_prefix_input",
                    help="Prefix used for folders (e.g. 'Draft' produces Draft_0001, Draft_0002, ...)",
                )

        # Dynamic Re-Packaging Action
        if st.session_state.email_drafts is not None:
            c_repack1, c_repack2 = st.columns([2, 1])
            with c_repack1:
                if st.button("🔄 Update Package Naming Style", help="Apply selected folder naming style to the ZIP and export package without regenerating draft contents or altering dataset"):
                    with st.spinner("Re-packaging drafts with selected naming style…"):
                        build_email_draft_package(
                            st.session_state.email_drafts,
                            naming_style=selected_style,
                            custom_prefix=custom_prefix_val,
                        )
                    st.success(f"Package rebuilt using **{selected_style}** folder naming! Download updated ZIP below.")

        # Main Generation Button
        if st.button("▶ Generate Email Drafts & Export Package", type="primary"):
            with st.spinner("Rendering email drafts and packaging ZIP export…"):
                drafts, skipped = generate_email_drafts(
                    df_clean,
                    subject_template=subject_tpl if subject_tpl else DEFAULT_SUBJECT_TEMPLATE,
                    body_template=body_tpl if body_tpl else DEFAULT_BODY_TEMPLATE,
                    max_drafts=max_drafts,
                    export_eml=export_eml,
                    export_package=True,
                    output_csv=EMAIL_DRAFTS_CSV,
                    naming_style=selected_style,
                    custom_prefix=custom_prefix_val,
                )
            st.session_state.email_drafts = drafts
            st.session_state.email_skipped = skipped
            st.success(f"Generated **{len(drafts)}** email drafts with **{selected_style}** folder naming.")

        # Post-generation dashboard & downloads
        if st.session_state.email_drafts is not None:
            drafts = st.session_state.email_drafts
            skipped = st.session_state.email_skipped or []

            st.markdown("#### Export Package Overview")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Eligible Records", eligible_count)
            col2.metric("Drafts Packaged", len(drafts))
            col3.metric("Skipped Records", len(skipped))
            zip_size_label = f"{EXPORT_ZIP_PATH.stat().st_size / 1024:.1f} KB" if EXPORT_ZIP_PATH.exists() else "Ready"
            col4.metric("ZIP Package Size", zip_size_label)

            # Prominent Download Controls
            if EXPORT_ZIP_PATH.exists() and len(drafts) > 0:
                st.markdown("#### Export Package Downloads")
                zip_bytes = EXPORT_ZIP_PATH.read_bytes()
                c_zip, c_csv = st.columns([2, 1])
                with c_zip:
                    st.download_button(
                        "📦 Download Complete ZIP Package (email_drafts_export.zip)",
                        data=zip_bytes,
                        file_name="email_drafts_export.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True,
                        key="download_drafts_zip_main",
                    )
                with c_csv:
                    if SUMMARY_CSV_PATH.exists():
                        st.download_button(
                            "📄 Download Summary CSV",
                            data=SUMMARY_CSV_PATH.read_bytes(),
                            file_name="drafts_summary.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key="download_drafts_summary_csv",
                        )
                st.caption("Active Package Archive: `output/email_drafts_export.zip`")

            # Diagnostic collapsible for skipped records
            if skipped:
                with st.expander(f"Skipped Records Diagnostic ({len(skipped)} records)", expanded=False):
                    st.markdown("**Reasons for exclusion:**")
                    for reason in skipped:
                        st.caption(f"• {reason}")

            if drafts:
                st.markdown("#### Drafts Summary Table (`drafts_summary.csv`)")
                summary_view = pd.DataFrame(drafts)
                cols_to_show = [c for c in ["draft_id", "folder_name", "recipient", "subject", "hotel_id", "hotel_name", "status"] if c in summary_view.columns]
                st.dataframe(summary_view[cols_to_show], use_container_width=True)

                st.markdown("#### Individual Draft Inspection & Downloads")
                draft_idx = st.selectbox(
                    "Select draft to inspect",
                    range(len(drafts)),
                    format_func=lambda i: f"{drafts[i]['draft_id']} → {drafts[i].get('folder_name', drafts[i]['draft_id'])} ({drafts[i]['recipient']})",
                )

                if draft_idx is not None:
                    sel_draft = drafts[draft_idx]
                    folder_name = sel_draft.get("folder_name", sanitize_filename(sel_draft['draft_id']))
                    st.caption(f"Folder Structure: `output/email_drafts_package/{folder_name}/`")

                    tab_txt, tab_eml, tab_meta = st.tabs(["Plain Text (email.txt)", "MIME Draft (email.eml)", "Metadata (metadata.json)"])

                    with tab_txt:
                        txt_content = create_text_message(sel_draft)
                        st.code(txt_content, language=None)
                        st.download_button(
                            f"⬇ Download {folder_name}/email.txt",
                            data=txt_content.encode("utf-8"),
                            file_name=f"{folder_name}_email.txt",
                            mime="text/plain",
                            key=f"dl_txt_{folder_name}",
                        )

                    with tab_eml:
                        eml_obj = create_eml_message(sel_draft)
                        eml_str = eml_obj.as_string()
                        st.code(eml_str, language="email")
                        st.download_button(
                            f"⬇ Download {folder_name}/email.eml",
                            data=eml_str.encode("utf-8"),
                            file_name=f"{folder_name}_email.eml",
                            mime="message/rfc822",
                            key=f"dl_eml_{folder_name}",
                        )

                    with tab_meta:
                        meta_dict = create_metadata_dict(sel_draft)
                        meta_json = json.dumps(meta_dict, indent=2, ensure_ascii=False)
                        st.json(meta_dict)
                        st.download_button(
                            f"⬇ Download {folder_name}/metadata.json",
                            data=meta_json.encode("utf-8"),
                            file_name=f"{folder_name}_metadata.json",
                            mime="application/json",
                            key=f"dl_json_{folder_name}",
                        )


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE: DOWNLOAD REPORTS (REFINED FILE CATALOG)
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Download Reports":
    st.markdown("""
    <div class="page-header">
        <div class="page-top-bar">
            <span class="page-step-badge">Data Exports</span>
            <div class="status-pill">
                <span class="status-dot"></span> Storage Catalog
            </div>
        </div>
        <h1 class="page-title">Downloadable Reports</h1>
        <p class="page-description">Access all generated datasets, summaries, and compiled ZIP packages directly from the server storage.</p>
    </div>
    """, unsafe_allow_html=True)

    catalog_entries = [
        {
            "title": "Complete Drafts Export ZIP",
            "badge": "Primary Archive",
            "desc": "Full ZIP archive with per-draft folders, standards-compliant email.eml, email.txt, and metadata.json.",
            "path": EXPORT_ZIP_PATH,
            "mime": "application/zip",
            "is_primary": True,
            "icon": "📦",
        },
        {
            "title": "Cleaned Dataset",
            "badge": "Stage 2 Output",
            "desc": "Standardized dataset with duplicates dropped, missing tokens audited, and schema types enforced.",
            "path": CLEANED_OUTPUT_CSV,
            "mime": "text/csv",
            "is_primary": False,
            "icon": "📊",
        },
        {
            "title": "Raw Collected Data",
            "badge": "Stage 1 Output",
            "desc": "Original ingested hotel listing records acquired from source HTML, CSV upload, or fallback data.",
            "path": RAW_OUTPUT_CSV,
            "mime": "text/csv",
            "is_primary": False,
            "icon": "🗂️",
        },
        {
            "title": "Drafts Summary Index",
            "badge": "Drafts Index",
            "desc": "Root-level index CSV tracking draft IDs, folder names, recipient addresses, and delivery status.",
            "path": OUTPUT_DIR / "drafts_summary.csv",
            "mime": "text/csv",
            "is_primary": False,
            "icon": "📋",
        },
        {
            "title": "Synthetic Benchmark Data",
            "badge": "Benchmark",
            "desc": "Machine-generated statistical records tagged with record_type = SYNTHETIC for evaluation.",
            "path": SYNTHETIC_OUTPUT_CSV,
            "mime": "text/csv",
            "is_primary": False,
            "icon": "🧬",
        },
        {
            "title": "Email Drafts Dataset",
            "badge": "Rendered Messages",
            "desc": "Tabular records containing rendered message subjects, bodies, and target recipient addresses.",
            "path": EMAIL_DRAFTS_CSV,
            "mime": "text/csv",
            "is_primary": False,
            "icon": "✉️",
        },
    ]

    for item in catalog_entries:
        p: Path = item["path"]
        exists = p.exists()
        size_str = f"{p.stat().st_size / 1024:.1f} KB" if exists else "Not generated"

        c_info, c_action = st.columns([3, 1])
        with c_info:
            if item["is_primary"]:
                badge_html = f'<span class="badge-primary-archive">{item["badge"]}</span>'
            elif item["badge"]:
                badge_html = f'<span class="badge-neutral">{item["badge"]}</span>'
            else:
                badge_html = ""

            st.markdown(f"""
            <div style="padding: 0.35rem 0;">
                <div style="font-size: 0.95rem; font-weight: 700; color: #F4F4F5; display: flex; align-items: center; gap: 0.5rem;">
                    <span>{item['icon']}</span> {item['title']} {badge_html}
                </div>
                <div style="font-size: 0.8rem; color: #A1A1AA; margin-top: 0.2rem;">{item['desc']}</div>
                <div style="font-size: 0.72rem; color: #71717A; margin-top: 0.25rem; font-family: 'JetBrains Mono', monospace;">
                    output/{p.name} · <span style="color: {'#F4F4F5' if exists else '#71717A'}; font-weight: 500;">{size_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c_action:
            st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)
            if exists:
                btn_type = "primary" if item["is_primary"] else "secondary"
                st.download_button(
                    label=f"⬇ Download {p.name}",
                    data=file_to_bytes(p),
                    file_name=p.name,
                    mime=item["mime"],
                    type=btn_type,
                    key=f"dl_cat_{p.name}",
                    use_container_width=True,
                )
            else:
                st.button(f"Pending Generation", disabled=True, key=f"dl_dis_{p.name}", use_container_width=True)

        st.markdown("<hr style='border: none; border-top: 1px solid #2C2E35; margin: 0.6rem 0 0.85rem 0;'>", unsafe_allow_html=True)

    # Legacy EML files if present
    eml_dir = OUTPUT_DIR / "eml_drafts"
    eml_files = list(eml_dir.glob("*.eml")) if eml_dir.exists() else []
    if eml_files:
        st.markdown(f"#### Individual .eml Files ({len(eml_files)} files)")
        for eml_path in eml_files[:8]:
            st.download_button(
                f"📄 {eml_path.name}",
                data=eml_path.read_bytes(),
                file_name=eml_path.name,
                mime="message/rfc822",
                key=f"eml_{eml_path.name}",
            )
        if len(eml_files) > 8:
            st.caption(f"… and {len(eml_files) - 8} more files stored in `output/eml_drafts/`")


# ═════════════════════════════════════════════════════════════════════════════
#  PAGE: PROJECT INFO
# ═════════════════════════════════════════════════════════════════════════════
elif page == "Project Info":
    st.markdown("""
    <div class="page-header">
        <div class="page-top-bar">
            <span class="page-step-badge">System Documentation</span>
            <div class="status-pill">
                <span class="status-dot"></span> Viva &amp; Lab Reference
            </div>
        </div>
        <h1 class="page-title">Project Information</h1>
        <p class="page-description">Architecture, technology stack, and compliance considerations for lab evaluation and viva examination.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="ui-card">
            <div class="ui-card-title">Academic &amp; Internship Details</div>
            <table style="width: 100%; font-size: 0.85rem; color: #E4E4E7; border-collapse: collapse;">
                <tr><td style="padding: 0.45rem 0; color: #A1A1AA;">Project Title</td><td style="padding: 0.45rem 0;">Web Data Collection, Data Preparation &amp; Automated Email System</td></tr>
                <tr><td style="padding: 0.45rem 0; color: #A1A1AA;">Organisation</td><td style="padding: 0.45rem 0;">Training Trains Software Technologies &amp; Institute</td></tr>
                <tr><td style="padding: 0.45rem 0; color: #A1A1AA;">Domain</td><td style="padding: 0.45rem 0;">Artificial Intelligence &amp; Data Science (B.Tech)</td></tr>
                <tr><td style="padding: 0.45rem 0; color: #A1A1AA;">Execution Environment</td><td style="padding: 0.45rem 0;">Localhost (Windows / Visual Studio Code)</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="ui-card">
            <div class="ui-card-title">Technology Stack</div>
            <table style="width: 100%; font-size: 0.85rem; color: #E4E4E7; border-collapse: collapse;">
                <tr><td style="padding: 0.45rem 0;"><code>requests</code></td><td style="padding: 0.45rem 0; color: #A1A1AA;">Permitted HTTP operations with timeouts &amp; custom user-agent</td></tr>
                <tr><td style="padding: 0.45rem 0;"><code>beautifulsoup4</code></td><td style="padding: 0.45rem 0; color: #A1A1AA;">HTML DOM parsing and card extraction</td></tr>
                <tr><td style="padding: 0.45rem 0;"><code>pandas</code></td><td style="padding: 0.45rem 0; color: #A1A1AA;">Dataframe manipulation, schema audit, and type coercion</td></tr>
                <tr><td style="padding: 0.45rem 0;"><code>streamlit</code></td><td style="padding: 0.45rem 0; color: #A1A1AA;">Reactive web interface &amp; file management</td></tr>
                <tr><td style="padding: 0.45rem 0;"><code>email</code> / <code>zipfile</code></td><td style="padding: 0.45rem 0; color: #A1A1AA;">RFC-2822 draft generation &amp; structured archive packaging</td></tr>
                <tr><td style="padding: 0.45rem 0;"><code>pytest</code></td><td style="padding: 0.45rem 0; color: #A1A1AA;">Automated test suite (157 unit &amp; integration tests)</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="ui-card">
            <div class="ui-card-title">Clean Project Directory Structure</div>
            <pre style="font-size: 0.76rem; background: #15161A; padding: 0.75rem; border-radius: 6px; border: 1px solid #2C2E35; color: #D4D4D8; overflow-x: auto;">
web_data_email_system/
├── app.py                      ← Modern Streamlit Dashboard
├── requirements.txt            ← Pinned Dependencies
├── README.md                   ← Project Guide &amp; Instructions
├── VIVA_PREPARATION.md         ← Comprehensive Viva Q&amp;A
├── data/
│   ├── sample_page.html        ← Bundled HTML
│   └── sample_data.csv         ← Bundled CSV
├── output/
│   ├── email_drafts_export.zip ← Structured ZIP Package
│   └── email_drafts_package/   ← Per-Draft Folders
├── src/
│   ├── data_collection.py
│   ├── data_cleaning.py
│   ├── synthetic_data.py
│   ├── email_automation.py
│   └── validation.py
└── tests/                      ← 157 Passing Automated Tests</pre>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="ui-card">
            <div class="ui-card-title">Ethical &amp; Academic Compliance</div>
            <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.82rem; color: #A1A1AA; line-height: 1.6;">
                <li>Respects robots.txt directives and adheres to polite scraping practices.</li>
                <li>Zero circumvention of login walls, paywalls, CAPTCHAs, or anti-bot defenses.</li>
                <li>All synthetic records are clearly labelled to prevent misleading demonstrations.</li>
                <li>Email generation is strictly local; emails are never sent without authorization.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
