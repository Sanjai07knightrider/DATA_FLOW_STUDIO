# DataFlow Studio — Web Data Collection, Data Preparation and Automated Email Generation System

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Tests](https://img.shields.io/badge/Tests-157%20Passed-4ADE80?logo=pytest&logoColor=white)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-Educational%20%2F%20Internship-818CF8)](#-academic--internship-context)

An end-to-end Python data pipeline and analytics dashboard demonstrating ethical web data collection, CSV schema validation, data preparation, synthetic benchmark generation, and standards-compliant email draft packaging.

Developed as a Data Science internship project at **Training Trains Software Technologies & Institute / DomainHostly.com**.

---

## 📌 Executive Summary

Modern data workflows demand robust end-to-end data pipelines capable of ingesting semi-structured data from web targets and user files, enforcing schema contracts, eliminating dirty records, augmenting datasets safely via synthetic data generation, and automating personalized communication workflows.

**DataFlow Studio** delivers this workflow inside an interactive, dark-themed dashboard built with Streamlit. The system operates strictly within a **local-only sandbox**: email drafts are generated as RFC-2822 `.eml`, `.txt`, and `.json` files packaged inside structured ZIP archives on local storage. **No live emails are dispatched automatically.**

---

## 🚀 Key Features

### 1. Multi-Source Data Collection
- **Deterministic Offline HTML Ingestion**: Built-in parser (`data/sample_page.html`) extracting structured hotel listings without requiring network connectivity.
- **Pre-Bundled CSV Fallback**: Fast offline dataset (`data/sample_data.csv`) for zero-dependency evaluations.
- **Permitted Public Web Scraping**: Live collection from approved educational endpoints (`books.toscrape.com`) utilizing polite rate-limiting (1-second delays), custom user-agent headers, and error handling.

### 2. Custom CSV Dataset Ingestion & Validation Engine
- **Browser File Uploader**: Accepts custom `.csv` files up to 20 MB and 50,000 rows.
- **Schema & Contract Inspection**: Audits presence of required columns (`hotel_name`) and optional columns (`location`, `category`, `price_inr`, `rating`, `reviews`, `amenities`, `availability`, `contact_email`).
- **Intelligent Alias Resolution**: Automatically maps non-standard column headers:
  - `name`, `hotel`, `property_name`, `hotelname` ➔ `hotel_name`
  - `email`, `mail`, `recipient_email`, `contact` ➔ `contact_email`
  - `price`, `tariff`, `rate`, `cost` ➔ `price_inr`
  - `stars`, `score` ➔ `rating`
  - `city`, `address`, `place` ➔ `location`
- **Original Preservation**: Saves raw user uploads separately in `output/` while feeding sanitized copies into downstream modules.

### 3. Data Cleaning & Preparation Pipeline
- **Text Normalization**: Trims leading/trailing whitespace and normalizes whitespace across text and location columns.
- **Deduplication**: Automatically detects and drops exact duplicate rows across all schema attributes.
- **Type Coercion**: Robustly converts prices, star ratings, and review numbers to numeric representations (`float`/`int`).
- **Missing Value Handling**: Converts blank tokens to formal NaN, imputes optional unpopulated fields with clean `N/A` fallbacks, and outputs comprehensive audit summaries.

### 4. Synthetic Data Generation Engine
- **Vocabulary-Based Synthesis**: Mirrors the distribution, price ranges, and category distributions of the cleaned dataset.
- **Reproducible Random Seed**: Configurable numeric seed guarantees identical benchmark dataset outputs across runs.
- **Safety Labeling**: Every synthetic record is tagged with `record_type = SYNTHETIC` and assigned RFC 2606 reserved domains (`@*.synthetic.example.com`) to prevent confusing benchmark data with genuine records.

### 5. Automated Email Draft Package Generator
- **Cleaned Data Coupling**: Drafts are rendered exclusively from the currently active cleaned dataset.
- **Recipient Validation**: RFC-compliant email regex validates recipient addresses; ineligible records are documented in an exclusion diagnostic.
- **Templating Engine**: Supports customizable subject lines and body text with dynamic variable placeholders (`{hotel_name}`, `{location}`, `{price_inr}`, etc.).
- **Local-Only Safety Guarantee**: Emails are strictly created as disk drafts. No SMTP transmissions occur without explicit developer reconfiguration.

### 6. Customizable Draft Folder Naming & ZIP Packaging
- **Custom Folder Naming Schemes**:
  1. `Draft ID`: Standard incremental folders (`DRAFT-0001`, `DRAFT-0002`).
  2. `Hotel Name`: Sanitized property name with collision prevention (e.g. `The_Grand_Palace_Hotel`).
  3. `Recipient Email`: Sanitized email address (e.g. `reservations_grandpalace_com`).
  4. `Custom Prefix + Number`: User-specified token producing `Prefix_0001`, `Prefix_0002`, etc.
- **Structured Package Output**:
  - `email.eml`: Standard RFC-2822 MIME draft file viewable in Outlook, Thunderbird, or Apple Mail.
  - `email.txt`: Human-readable plain text message.
  - `metadata.json`: Complete draft metadata (ID, recipient, hotel ID, timestamp, status).
  - `drafts_summary.csv`: Master root-level index linking all drafts.
  - `email_drafts_export.zip`: Compiled ZIP archive preserving folder structures.

---

## 🛠️ Technology Stack

| Layer | Component | Version | Purpose |
|---|---|---|---|
| **Language** | Python | 3.11+ / 3.14 | Core execution runtime |
| **Web Framework** | Streamlit | ≥1.28.0 | Interactive dark-mode dashboard |
| **Data Analysis** | Pandas | ≥2.0.0 | Tabular manipulation, cleaning, and CSV I/O |
| **Web Scraping** | Requests | ≥2.28.0 | HTTP client with timeouts & custom user-agent |
| **DOM Parsing** | BeautifulSoup4 | ≥4.12.0 | HTML element selection and card parsing |
| **Parser Backend** | LXML | ≥4.9.0 | High-performance HTML parser |
| **Synthesis** | Faker | ≥20.0.0 | Vocabulary pools for synthetic benchmark records |
| **Testing** | Pytest | ≥7.4.0 | Automated unit and integration testing |
| **Draft Encoding** | Python `email` | Standard Lib | RFC-2822 MIME message formatting |
| **Packaging** | Python `zipfile` | Standard Lib | Structured ZIP archive compilation |
| **Config** | Python-Dotenv | ≥1.0.0 | Environment variable loader template |

---

## 🗂️ Project Directory Structure

```
web_data_email_system/
├── app.py                          # Streamlit dashboard & UI interface
├── requirements.txt                # Pinned dependencies
├── README.md                       # Comprehensive project documentation
├── VIVA_PREPARATION.md             # 30-question viva and lab reference guide
├── .env.example                    # Template for optional SMTP configuration
├── .gitignore                      # Git exclusion rules for secrets & generated data
│
├── data/                           # Safe, bundled demo data (committed to Git)
│   ├── sample_page.html            # 12 hotel listing cards for offline HTML ingestion
│   └── sample_data.csv             # 12 offline hotel records with valid example emails
│
├── src/                            # Modular Python source packages
│   ├── __init__.py                 # Package marker
│   ├── data_collection.py          # Module 1: HTML parsing, fallback loading & requests
│   ├── data_cleaning.py            # Module 2: Pandas normalization, deduplication & coercion
│   ├── synthetic_data.py           # Module 3: Statistical synthetic record generator
│   ├── email_automation.py         # Module 4: Email drafting, folder naming & ZIP packager
│   └── validation.py               # Module 5: CSV schema checks, alias matching & email regex
│
├── tests/                          # 157 Automated Pytest suites (100% pass rate)
│   ├── __init__.py
│   ├── conftest.py                 # Shared pytest fixtures and mock DataFrames
│   ├── test_data_collection.py     # 16 tests: HTML parsing, fallback CSV, error handling
│   ├── test_data_cleaning.py       # 14 tests: Deduplication, numeric conversion, imputation
│   ├── test_synthetic_data.py      # 13 tests: Reproducibility, seed controls, schema tags
│   ├── test_email_automation.py    # 40 tests: RFC-2822 headers, MIME encoding, validation
│   ├── test_upload_validation.py   # 33 tests: CSV upload contracts, alias fixes, pipeline integrity
│   └── test_email_export_package.py# 41 tests: Per-draft folders, naming schemes & ZIP packaging
│
└── output/                         # Runtime generated output directory (ignored by Git)
    ├── raw_collected_data.csv
    ├── cleaned_data.csv
    ├── synthetic_data.csv
    ├── email_drafts.csv
    ├── drafts_summary.csv
    ├── email_drafts_export.zip     # Complete structured ZIP export
    └── email_drafts_package/       # Per-draft subfolders (DRAFT-xxxx/)
```

---

## 💻 Installation & Setup (Windows Guide)

### Prerequisites
- Windows 10 or 11
- Python 3.11, 3.12, or 3.14 installed (`python --version` to verify)
- Git installed (`git --version` to verify)

### Step 1: Open Terminal
Open **PowerShell**, **Windows Terminal**, or your IDE's integrated terminal (VS Code).

### Step 2: Navigate to Project Directory
```powershell
cd D:\intern\TrainingTrains_DataScience\web_data_email_system
```

### Step 3: Create & Activate Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\activate
```
*(Your prompt will now display `(.venv)`).*

### Step 4: Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Launch the Streamlit Dashboard
```powershell
streamlit run app.py
```
> The dashboard will open automatically in your browser at:  
> **http://localhost:8501**

*Alternative launch command if `streamlit` is not on your direct Windows PATH:*
```powershell
python -m streamlit run app.py
```

---

## 🧪 Running the Automated Test Suite

The test suite validates data ingestion, schema validation, cleaning rules, synthetic generation, RFC-2822 compliance, folder naming styles, and ZIP packaging integrity.

```powershell
# Run all 157 tests with verbose output
python -m pytest tests/ -v

# Run a specific module's test suite
python -m pytest tests/test_email_export_package.py -v
python -m pytest tests/test_upload_validation.py -v
python -m pytest tests/test_data_cleaning.py -v

# Run with concise summary
python -m pytest tests/ --tb=short
```

**Current Test Status:**
```
============================= 157 passed in 3.45s =============================
Platform: Windows / Python 3.14.3 / pytest 9.1.1
```

---

## 📋 CSV Schema & Upload Requirements

When uploading your own dataset via **Data Collection ➔ Upload Custom CSV**, the schema engine enforces the following contract:

| Column Name | Status | Accepted Aliases | Description | Example |
|---|---|---|---|---|
| `hotel_name` | **Required** | `name`, `hotel`, `property_name`, `hotelname` | Primary hotel identifier | `The Grand Palace Hotel` |
| `contact_email` | **Required for Drafts** | `email`, `mail`, `recipient_email`, `contact` | Valid recipient email | `reservations@example.com` |
| `category` | Optional | `type`, `hotel_type`, `segment` | Accommodation class | `Luxury`, `Resort`, `Budget` |
| `location` | Optional | `city`, `address`, `place`, `destination` | City, State, Country | `Mumbai, Maharashtra, India` |
| `price_inr` | Optional | `price`, `tariff`, `rate`, `cost`, `room_rate` | Nightly tariff | `8500` |
| `rating` | Optional | `stars`, `score`, `user_rating` | Numeric score (1.0 to 5.0) | `4.7` |
| `reviews` | Optional | `review_count`, `num_reviews` | Review count | `1240` |
| `amenities` | Optional | `facilities`, `features` | Comma-separated amenities | `Pool, Spa, WiFi, Gym` |
| `availability` | Optional | `status`, `room_status` | Room status | `Available` |

**Upload Guardrails:**
- **Max File Size:** 20 MB
- **Max Rows:** 50,000 records
- **Encoding:** Standard UTF-8 CSV
- Unmatched non-standard columns are safely preserved as supplementary attributes.

---

## 📦 Email Draft Export Package Structure

When generating drafts in the **Email Drafts** module, the export engine compiles an archive formatted as follows:

```
email_drafts_export.zip
├── drafts_summary.csv                      # Root-level index of all drafts
├── DRAFT-0001/                             # (or named by Hotel Name, Email, etc.)
│   ├── email.eml                           # RFC-2822 standards-compliant draft
│   ├── email.txt                           # Formatted plain-text draft
│   └── metadata.json                       # Audit metadata (timestamp, IDs, status)
├── DRAFT-0002/
│   ├── email.eml
│   ├── email.txt
│   └── metadata.json
└── ...
```

### Folder Naming Schemes:
1. **Draft ID (Default):** Produces sequential folders `DRAFT-0001`, `DRAFT-0002`, ...
2. **Hotel Name:** Produces sanitized directory names like `The_Grand_Palace_Hotel` (with collision suffixes `_2` if duplicate names exist).
3. **Recipient Email:** Produces sanitized email directories like `reservations_grandpalace_example_com`.
4. **Custom Prefix + Number:** User enters prefix `Client` to produce `Client_0001`, `Client_0002`, etc.

---

## ⚖️ Privacy, Security & Ethical Guidelines

- **Zero Automatic Email Dispatching**: All emails are generated strictly as local files. No background network requests or SMTP connections are initiated.
- **Safe Synthetic Data**: Generated benchmark records utilize reserved `.synthetic.example.com` domains in compliance with RFC 2606.
- **Ethical Web Scraping**: Live scraping requests utilize polite user-agent identification and 1-second delays between page fetches. No paywalls, CAPTCHAs, or authentication barriers are bypassed.
- **Credential Protection**: No secrets, passwords, or API tokens are hardcoded. Runtime outputs and private uploads are excluded from Git via `.gitignore`.

---

## ⚠️ Known Limitations

1. **Local-Only Email Generation**: The system does not dispatch live SMTP transmissions by default. This is an intentional safety architecture for academic evaluation.
2. **Python 3.14 Compatibility**: Fully verified and compatible with Python 3.14.3 on Windows.
3. **Public Demo Endpoint**: The online source connects to `books.toscrape.com`, normalizing public data to the hotel schema for live connectivity demonstration. Offline sources (`sample_page.html` and `sample_data.csv`) provide 100% deterministic local evaluations.

---

## 🎓 Academic & Internship Context

- **Project Title:** Web Data Collection, Data Preparation and Automated Email Generation System
- **Organisation:** Training Trains Software Technologies & Institute / DomainHostly.com
- **Curriculum Domain:** Artificial Intelligence and Data Science (B.Tech)
- **Environment:** Visual Studio Code · Windows PowerShell · Localhost Sandbox
