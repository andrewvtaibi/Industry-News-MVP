# Company Reports and Information Engine

A lightweight tool for searching companies or ticker symbols and
retrieving headlines, press releases, and interactive stock charts.

---

## Quick Start (End User)

**One step:**

> Double-click **`Launch BioNews.bat`** in Windows Explorer.

The browser opens automatically to `http://localhost:8000`.
Keep the black window open while you use the app — closing it stops
the server.

---

## What You Can Do

| Feature | How to use it |
|---|---|
| Search by company name | Type "Pfizer" in the search bar, press Enter |
| Search by ticker symbol | Type "PFE" in the search bar, press Enter |
| Batch search | Upload a CSV file (company names or tickers, one per row) |
| Switch timeframe | Click **Past Week** (7 days) or **Past Month** (30 days) |
| Switch content type | Click **Headlines**, **Press releases**, or **Stock price** |

### Headlines
Recent news articles about the company, sourced from Google News.
Each result links to the original article.

### Press Releases
Company-issued statements from PR Newswire, GlobeNewswire, and
BusinessWire only. No third-party editorial content.

### Stock Price
An interactive TradingView chart for the resolved ticker symbol.
If a ticker cannot be resolved, a clear message is shown.

### CSV Upload
Create a plain `.csv` file with one company name or ticker per row:

```
company
PFE
MRNA
Regeneron
Bristol-Myers Squibb
```

Upload it using the yellow card (top-right of the page). The app
returns results for each entry, collapsible by company.

**Limits:** 50 rows maximum, 1 MB maximum file size, UTF-8 encoding.

---

## If Something Goes Wrong

| Symptom | What to check |
|---|---|
| Browser says "site cannot be reached" | Make sure the black CMD window is still open |
| Black window closed immediately | Open `logs\launch.log` in Notepad for the error |
| "Virtual environment not found" message | See First-Time Setup below |
| No results returned | Try a longer timeframe (Past Month), or check your internet connection |
| Press releases empty | Some companies publish infrequently; try Past Month |
| Stock chart blank or not loading | Ticker not resolved — try the exact ticker symbol (e.g. NVO, PFE); the chart requires an internet connection to load |

### Reading the log file

If the app fails to start, open `logs\launch.log` in Notepad.
The last few lines will show the specific error.

---

## First-Time Setup

This is only needed once. If `Launch BioNews.bat` works, skip this.

1. Open a terminal (search "cmd" in the Windows Start menu).
2. Navigate to the project folder:
   ```
   cd "c:\Users\andre\OneDrive\Desktop\App Development\Bio-news-mvp"
   ```
3. Create the virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
4. Close the terminal. Double-click `Launch BioNews.bat`.

---

## Running the Tests

Open a terminal in the project folder, then run:

```
.venv\Scripts\python.exe -m pytest tests\ -m "not integration" -v
```

Expected output: **124 passed** (unit tests, no network required).

To also run live network tests (requires internet):

```
.venv\Scripts\python.exe -m pytest tests\test_integration.py -v
```

Expected output: **10 passed** (real RSS feeds).

---

## Stopping the App

Close the black CMD window, or press `Ctrl+C` inside it.
The browser tab will remain open but will show "connection refused"
until the server is restarted.

---

## Project Structure (Reference)

```
Bio-news-mvp/
  Launch BioNews.bat   <- double-click to start
  launch.py            <- launcher logic (auto-opens browser)
  server/              <- FastAPI backend
  static/              <- HTML/CSS/JS frontend
  data/tickers.json    <- ticker symbol lookup table
  tests/               <- automated test suite
  logs/launch.log      <- startup log (check here on errors)
  app/                 <- original CLI aggregator (unchanged)
```

---

## Security Notes

- All user input is sanitized before use (XSS and injection protected).
- Rate limiting: 30 searches per minute per IP address.
- CSV uploads: validated for size, row count, and encoding.
- No user data is stored or transmitted beyond fetching public RSS feeds.
- Error messages never expose internal server details.
