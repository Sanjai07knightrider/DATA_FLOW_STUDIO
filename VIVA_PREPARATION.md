# VIVA PREPARATION GUIDE
## Web Data Collection, Data Preparation and Automated Email Generation System

**Internship Project — Training Trains Software Technologies & Institute / DomainHostly.com**  
**Student Domain:** B.Tech Artificial Intelligence and Data Science

---

## 📖 How to Use This Guide

Read each section carefully. For every viva question, first try to answer it yourself, then check the provided answer. The key is to understand *why* each design decision was made, not just *what* was done.

---

## 🔄 Project Summary (Simple Explanation)

This project is like a **smart data pipeline**. Imagine you want to:

1. **Collect** hotel advertisement details from websites (like names, prices, locations).
2. **Clean** that data — remove duplicates, fix missing values, standardise formats.
3. **Expand** the dataset by creating fake-but-realistic records for testing.
4. **Communicate** — automatically write personalised emails for each hotel.
5. **Show everything** on a nice web dashboard that anyone can use.

All of this is done using Python, following ethical and professional standards.

---

## 📦 Module-by-Module Explanation

### Module 1: Data Collection (`data_collection.py`)

**What it does:**
- Reads hotel data from a local HTML file (`data/sample_page.html`).
- Alternatively, fetches book listings from `books.toscrape.com` (a demo site for practice).
- Falls back to a pre-bundled CSV if neither is available.
- Saves raw collected data to `output/raw_collected_data.csv`.

**Key concepts:**
- **BeautifulSoup** parses HTML by finding elements with `find()` and `find_all()`.
- **Requests** sends HTTP GET requests with a timeout and custom User-Agent header.
- **Error handling** catches `TimeoutError`, `HTTPError`, `ConnectionError`.
- **Rate limiting** — 1-second sleep between page requests is polite and avoids overloading servers.

---

### Module 2: Data Cleaning (`data_cleaning.py`)

**What it does:**
- Converts raw records to a Pandas DataFrame.
- Replaces empty strings with `NaN`.
- Strips and normalises whitespace.
- Converts price, rating, and reviews to numeric types.
- Removes duplicate rows.
- Drops rows where all required fields are missing.
- Fills remaining NaN in text columns with `'N/A'`.
- Saves cleaned data to `output/cleaned_data.csv`.

**Key concepts:**
- `df.replace("", pd.NA)` — replaces empty strings.
- `df.drop_duplicates()` — removes exact duplicate rows.
- `pd.to_numeric(..., errors='coerce')` — converts text to numbers, sets invalid to NaN.
- `str.strip().str.replace(r"\s+", " ", regex=True)` — normalises whitespace.
- Raw data and cleaned data are **separate files** — never overwrite original data.

---

### Module 3: Synthetic Data Generation (`synthetic_data.py`)

**What it does:**
- Uses the cleaned DataFrame as a structural reference.
- Generates configurable number of fake-but-realistic hotel records.
- Uses Python's `random.Random` with a fixed seed for reproducibility.
- Labels all records as `record_type = SYNTHETIC`.
- Uses `@synthetic.example.com` domain for all generated emails.
- Saves to `output/synthetic_data.csv`.

**Key concepts:**
- **Seed** — `random.Random(42)` always produces the same sequence. Change seed → different data.
- Synthetic emails use `@synthetic.example.com` — a clearly non-real domain (per RFC 2606).
- All price/rating values are derived from ranges observed in real data — so they're realistic but not copies.

---

### Module 4: Email Draft Generation (`email_automation.py`)

**What it does:**
- Takes cleaned DataFrame records.
- Validates each `contact_email` using regex before using it.
- Renders a subject line and body from configurable templates.
- Creates draft dicts with `draft_id`, `to_email`, `subject`, `body`.
- Saves drafts to `output/email_drafts.csv`.
- Optionally saves individual `.eml` files.
- **Never sends emails automatically.**

**Key concepts:**
- `{field}` placeholders in templates are filled using `str.format(**record)`.
- `email.mime.multipart.MIMEMultipart` builds RFC 2822 compliant messages.
- SMTP is only enabled when environment variables are set AND user explicitly passes `confirmed=True`.
- Missing template fields → replaced with `"N/A"` instead of raising `KeyError`.

---

### Module 5: Validation (`validation.py`)

**What it does:**
- `is_valid_email()` — validates email format with regex.
- `validate_dataframe()` — checks columns and minimum row count.
- `validate_price()` — checks if price is a positive number.
- `sanitise_email()` — strips and lowercases email, returns empty string if invalid.

---

### Module 6: Tests (`tests/`)

**What it does:**
- Provides automated Pytest tests for all four main modules.
- Uses local fixture data — no internet required to run tests.
- Covers: valid inputs, invalid inputs, edge cases, empty data, file I/O.

---

## 📚 Library Explanations

| Library | What it is | Why we use it |
|---|---|---|
| **requests** | HTTP client library | Sends GET requests to websites with timeout, headers |
| **BeautifulSoup4** | HTML parser | Extracts specific elements from webpage HTML |
| **lxml** | XML/HTML parser backend | Faster and more robust than Python's built-in HTML parser |
| **pandas** | Data analysis library | DataFrame operations: cleaning, filtering, grouping, export |
| **streamlit** | Web UI framework | Creates interactive dashboards from pure Python — no HTML/CSS needed |
| **pytest** | Testing framework | Writes and runs unit tests; provides fixtures, assertions, coverage |
| **faker** | Fake data generator | Vocabulary pools for creating realistic-sounding synthetic records |
| **email** (built-in) | Email composition | Creates RFC 2822 .eml files with headers and body |
| **csv** (built-in) | CSV reading/writing | Reads and writes comma-separated value files |
| **re** | Regular expressions | Pattern matching for email validation |
| **python-dotenv** | .env file loader | Loads environment variables from .env file securely |

---

## 🔢 Step-by-Step Workflow

```
START
  │
  ▼
[1] User clicks "Collect Data" in the dashboard
      → data_collection.py reads sample_page.html
      → BeautifulSoup finds all <div class="hotel-card"> elements
      → Extracts: name, category, location, price, rating, etc.
      → Saves raw_collected_data.csv
  │
  ▼
[2] User clicks "Run Data Cleaning"
      → data_cleaning.py receives raw records list
      → Converts to pandas DataFrame
      → Replaces empty strings with NaN
      → Normalises whitespace with str.strip() and regex
      → Converts price/rating to float, reviews to int
      → Removes duplicate rows with drop_duplicates()
      → Drops rows with all required fields missing
      → Fills remaining NaN in text columns with 'N/A'
      → Saves cleaned_data.csv
  │
  ▼
[3] User clicks "Generate Synthetic Data"
      → synthetic_data.py uses cleaned DataFrame for schema reference
      → Uses random.Random(seed) to generate N records
      → Each record gets a hotel name, category, price, rating, email
      → All records labelled record_type = "SYNTHETIC"
      → Saves synthetic_data.csv
  │
  ▼
[4] User clicks "Generate Email Drafts"
      → email_automation.py iterates over cleaned DataFrame rows
      → Validates each contact_email with regex
      → Skips invalid emails (logs reason)
      → Renders subject and body templates with {field} substitution
      → Creates MIME email objects → saves .eml files
      → Saves email_drafts.csv
  │
  ▼
[5] User downloads CSV reports from "Download Reports"

END
```

---

## ❓ Viva Questions and Answers

### 🐍 Python Basics

**Q1. What is the difference between a list and a dictionary in Python?**

A list (`[1, 2, 3]`) is an ordered collection of items accessed by index (position number). A dictionary (`{"name": "Hotel A"}`) is an unordered collection of key-value pairs accessed by key. In this project, we use lists of dictionaries to represent records — each dict is one row with column names as keys.

---

**Q2. What are `f-strings` and why are they used?**

F-strings (formatted string literals) allow you to embed Python expressions directly inside strings using `{}`. Example:
```python
name = "Grand Hotel"
print(f"Welcome to {name}!")  # Output: Welcome to Grand Hotel!
```
They are faster and more readable than `.format()` or `%` formatting.

---

**Q3. What is a `virtual environment` and why should you use one?**

A virtual environment is an isolated Python environment where you can install packages without affecting the system-wide Python installation. It prevents version conflicts between different projects. Created with:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

---

**Q4. What does `if __name__ == "__main__":` mean?**

This checks if the script is being run directly (not imported as a module). Code inside this block runs only when you execute the file directly (`python data_collection.py`), not when another file imports it. This is good practice for making modules both importable and standalone.

---

### 🌐 Web Scraping

**Q5. What is web scraping?**

Web scraping is the automated process of extracting data from websites by downloading the HTML content and parsing it to identify and extract specific information. Tools like `requests` (download HTML) and `BeautifulSoup` (parse HTML) are used together.

---

**Q6. What is BeautifulSoup and how does it work?**

BeautifulSoup is a Python library that parses HTML and XML documents, turning them into a parse tree. You can then search for elements by tag name, class, ID, or attributes:
```python
soup = BeautifulSoup(html_content, "lxml")
cards = soup.find_all("div", class_="hotel-card")
name = soup.find("h2", class_="hotel-name").get_text(strip=True)
```

---

**Q7. What is robots.txt?**

`robots.txt` is a file websites place at their root URL (e.g., `https://example.com/robots.txt`) to specify which pages bots can and cannot access. Ethical scrapers check this file and respect its directives. Our project uses `books.toscrape.com`, which permits scraping.

---

**Q8. What is rate limiting in web scraping?**

Rate limiting means deliberately pausing between requests to avoid overloading the server. In this project: `time.sleep(1.0)` — a 1-second delay between page requests. Without this, rapid requests could be interpreted as a DDoS attack and get your IP blocked.

---

**Q9. Why do we set a custom User-Agent header?**

The User-Agent header identifies your HTTP client to the server. A custom, descriptive User-Agent like:
```
"Mozilla/5.0 (Educational-Demo-Bot/1.0; +https://github.com/example)"
```
is more honest and polite than pretending to be a regular browser. It helps website owners understand who is accessing their server.

---

**Q10. What is a request timeout and why is it important?**

A timeout (`timeout=15`) tells the `requests` library to stop waiting for a response after 15 seconds. Without a timeout, your program could hang indefinitely if the server is slow or unreachable. Always set a timeout in production code.

---

### 🐼 Pandas and Data Cleaning

**Q11. What is a Pandas DataFrame?**

A DataFrame is a 2-dimensional labelled data structure (like a table or spreadsheet) with rows and columns. Each column can have a different data type. In this project:
```python
df = pd.DataFrame(records)  # Convert list of dicts to DataFrame
```

---

**Q12. What does `pd.to_numeric(series, errors='coerce')` do?**

It converts a Series to numeric values. The `errors='coerce'` argument means: if a value cannot be converted (e.g., the string `"N/A"`), set it to `NaN` instead of raising an error. This is safer than using `astype(float)` directly.

---

**Q13. How do you remove duplicate rows in Pandas?**

```python
df.drop_duplicates(inplace=True)
```
This removes rows where all column values are identical. You can also specify a subset of columns:
```python
df.drop_duplicates(subset=["hotel_name", "location"], inplace=True)
```

---

**Q14. What is `NaN` in Pandas?**

NaN stands for "Not a Number". It represents a missing or undefined value. In Pandas:
- `df.isnull()` returns a boolean DataFrame showing where NaN values are.
- `df.fillna("N/A")` replaces NaN with a specified value.
- `df.dropna()` removes rows with any NaN.

---

**Q15. Why do we preserve raw data separately from cleaned data?**

To maintain **data lineage** — the ability to trace back to the original source. If cleaning introduces a mistake, you can go back to the raw data. Also, different analyses may need different levels of cleaning. In this project: `raw_collected_data.csv` is saved first, then `cleaned_data.csv` separately.

---

**Q16. What does `str.strip().str.replace(r"\s+", " ", regex=True)` do?**

- `.str.strip()` — removes leading and trailing whitespace from each string.
- `.str.replace(r"\s+", " ", regex=True)` — replaces any run of multiple whitespace characters (spaces, tabs, newlines) with a single space.
- Together: `"  Hello   World  "` → `"Hello World"`.

---

### 🔬 Synthetic Data

**Q17. What is synthetic data?**

Synthetic data is artificially generated data that mimics the statistical properties of real data but does not contain any actual personal information. It is used for testing, training machine learning models, and demonstrations when real data is sensitive or scarce.

---

**Q18. How is reproducibility achieved in synthetic data generation?**

By using a fixed random seed:
```python
rng = random.Random(seed)  # seed=42
```
Every time you run the code with `seed=42`, you get the exact same sequence of random numbers → same synthetic records. Changing the seed produces different records.

---

**Q19. Why do synthetic emails use `@synthetic.example.com`?**

`example.com` is reserved by IANA (Internet Assigned Numbers Authority) for use in documentation and examples. It is guaranteed to never be a real commercial domain. Using `@synthetic.example.com` clearly signals that the email address is not real and prevents accidental use.

---

**Q20. How do you ensure synthetic data doesn't copy real personal information?**

- Hotel names are generated from vocabulary pools (prefixes + suffixes), not copied from real records.
- Email addresses use `@synthetic.example.com` — a clearly fake domain.
- All records have `record_type = "SYNTHETIC"` as a label.
- The reference DataFrame is only used to derive statistical ranges (min/max price, rating), not to copy values.

---

### 📧 Email Generation

**Q21. What is an `.eml` file?**

An `.eml` file is an email message stored in RFC 2822 format — the standard format for email messages. It contains headers (To, From, Subject) and the message body. `.eml` files can be opened in email clients like Outlook or Thunderbird. In this project, we generate `.eml` drafts using Python's `email.mime` module.

---

**Q22. Why are emails never sent automatically by default?**

Automatically sending emails without explicit human confirmation is a safety and compliance risk. Accidental mass-sending to incorrect recipients could:
- Violate anti-spam laws (GDPR, CAN-SPAM Act).
- Damage the sender's reputation.
- Cause unintended disclosures.

The project generates draft files only. SMTP sending requires setting environment variables AND passing `confirmed=True` explicitly.

---

**Q23. How do you validate an email address in Python?**

Using regular expressions:
```python
import re
pattern = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
is_valid = bool(pattern.match("user@example.com"))  # True
```
This checks the basic structural format. It does NOT verify that the address actually exists (that would require DNS lookup or SMTP verification).

---

**Q24. What is a string template and how is it used for email generation?**

A template is a string with `{placeholders}` that get replaced with actual values:
```python
template = "Dear {hotel_name} Team, your price is ₹{price_inr}."
record = {"hotel_name": "Grand Hotel", "price_inr": 5000}
result = template.format(**record)
# → "Dear Grand Hotel Team, your price is ₹5000."
```

---

**Q25. How are SMTP credentials kept secure?**

Using environment variables loaded from a `.env` file:
```python
import os
password = os.environ.get("SMTP_PASSWORD", "")
```
The `.env` file is listed in `.gitignore` so it is never committed to version control. The `.env.example` file shows the required variable names without actual values.

---

### 🧪 Testing

**Q26. What is Pytest?**

Pytest is a Python testing framework. You write test functions starting with `test_`, and pytest automatically discovers and runs them. Assertions use Python's built-in `assert` keyword:
```python
def test_is_valid_email():
    assert is_valid_email("user@example.com") is True
    assert is_valid_email("bad") is False
```

---

**Q27. What is a test fixture in Pytest?**

A fixture is a reusable piece of test setup, defined with the `@pytest.fixture` decorator:
```python
@pytest.fixture
def sample_records():
    return [{"hotel_name": "Test", "price_inr": "1000"}]

def test_cleaning(sample_records):
    df, _ = clean_data(sample_records)
    assert len(df) > 0
```
Pytest automatically passes the fixture's return value to test functions that declare it as a parameter.

---

**Q28. Why should tests not require internet access or real SMTP credentials?**

Tests must be **deterministic** — they should always produce the same result regardless of external conditions (internet availability, server state). This is achieved by using:
- Local fixture data instead of live web requests.
- `monkeypatch` to remove environment variables.
- `tmp_path` fixture to create temporary directories.

---

**Q29. What is `tmp_path` in Pytest?**

`tmp_path` is a built-in Pytest fixture that provides a temporary directory unique to each test run. Files created inside it are automatically cleaned up after the test. Used to test file I/O without cluttering the project directory:
```python
def test_save_csv(tmp_path):
    output = tmp_path / "test.csv"
    save_raw_csv(records, output_path=output)
    assert output.exists()
```

---

**Q30. What is `monkeypatch` in Pytest?**

`monkeypatch` is a Pytest fixture that temporarily modifies attributes, environment variables, or functions during a test, then automatically restores the original values afterward:
```python
def test_smtp_without_credentials(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    result = send_draft_via_smtp(draft, confirmed=True)
    assert result is False
```

---

### 🔧 Important Code Sections Explained

**Why use `errors='coerce'` in pd.to_numeric?**
```python
df["price_inr"] = pd.to_numeric(df["price_inr"], errors='coerce')
```
Without `errors='coerce'`, a single non-numeric value like `"N/A"` would crash the entire conversion. With `errors='coerce'`, it becomes `NaN` — safe and handleable.

---

**Why use `inplace=True` carefully?**
```python
df.drop_duplicates(inplace=True)
```
`inplace=True` modifies the DataFrame directly in memory without creating a copy. This is memory-efficient. However, be careful — once done, the original state is gone unless you made a copy first.

---

**Why do we check `if not records` before processing?**
```python
if not records:
    return [], ["DataFrame is empty"]
```
Defensive programming — always check for empty inputs before processing them to avoid `IndexError` or `AttributeError` on empty collections.

---

**Why does `_extract_hotel_card` have a try/except around it?**
```python
try:
    ...
except Exception as exc:
    logger.exception("Error extracting hotel card: %s", exc)
    return None
```
Web pages can have unexpected structures. Wrapping extraction in try/except ensures one malformed card doesn't crash the entire collection process.

---

## 🐛 Common Errors and Troubleshooting

| Error | Likely Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'bs4'` | Package not installed | `pip install beautifulsoup4` |
| `ModuleNotFoundError: No module named 'streamlit'` | Streamlit not installed | `pip install streamlit` |
| `FileNotFoundError: sample_page.html` | Running from wrong directory | `cd web_data_email_system` first |
| Tests fail with `import` error | sys.path not set correctly | Run `python -m pytest` not `pytest` |
| `KeyError` in template rendering | Field name in template doesn't match column name | Check column names in DataFrame |
| Empty draft list generated | All emails are invalid | Check `contact_email` column in cleaned data |
| Streamlit shows blank page | Syntax error in app.py | Check terminal for Python traceback |
| `ConnectionError` on online fetch | No internet connection | Switch to "Local HTML" source |

---

## 🗣️ Tips for the Viva

1. **Run the app before the viva** — know what each button does from personal experience.
2. **Understand the data flow** — be able to explain what happens from click to CSV.
3. **Know why** — for every design decision, be ready to explain *why* that approach was chosen.
4. **Ethical awareness** — emphasise what you *don't* do: no bypassing auth, no auto-sending emails, no hardcoded credentials.
5. **Be honest about limitations** — no project is perfect; show that you understand limitations.
6. **Show the tests** — run `python -m pytest tests/ -v` during the demo to prove they pass.
7. **Trace a single record** — be ready to trace one hotel record from HTML → raw CSV → cleaned CSV → email draft.
