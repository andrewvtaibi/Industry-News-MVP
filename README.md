# Company Reports and Information Engine

A lightweight tool for searching companies or ticker symbols and
retrieving headlines, press releases, and interactive stock charts.

---

## Quick Start (End User)

### Windows

**One step:**

> Double-click **`Launch BioNews.bat`** in Windows Explorer.

The browser opens automatically to `http://localhost:8000`.
Keep the black window open while you use the app — closing it
stops the server.

### Mac

**One step:**

> Double-click **`launch_macos.sh`** in Finder.

If double-clicking does nothing, right-click the file →
**Open With → Terminal**.

The browser opens automatically to `http://localhost:8000`.
Keep the Terminal window open while you use the app — closing
it stops the server.

> **First time on Mac?** See [Mac First-Time Setup](#mac-first-time-setup)
> below before running the script.

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
| Browser says "site cannot be reached" | Make sure the launcher window is still open |
| Launcher window closed immediately | Open `logs/launch.log` for the error (Notepad on Windows, TextEdit on Mac) |
| "Virtual environment not found" message | See First-Time Setup below for your OS |
| No results returned | Try a longer timeframe (Past Month), or check your internet connection |
| Press releases empty | Some companies publish infrequently; try Past Month |
| Stock chart blank or not loading | Ticker not resolved — try the exact ticker symbol (e.g. NVO, PFE); the chart requires an internet connection to load |
| Mac: `launch_macos.sh` opens in a text editor | Right-click → Open With → Terminal |
| Mac: "permission denied" when running the script | Run `chmod +x launch_macos.sh` in Terminal first |

### Reading the log file

If the app fails to start, open `logs/launch.log`.

- **Windows:** right-click the file → Open With → Notepad
- **Mac:** double-click the file, or run `open logs/launch.log` in Terminal

The last few lines will show the specific error.

---

## First-Time Setup

### Windows First-Time Setup

This is only needed once. If `Launch BioNews.bat` already works, skip this.

1. Open a terminal (search "cmd" in the Windows Start menu).
2. Navigate to the project folder:
   ```
   cd "path\to\Bio-news-mvp"
   ```
3. Create the virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
4. Close the terminal. Double-click `Launch BioNews.bat`.

---

### Mac First-Time Setup

This is only needed once. If `launch_macos.sh` already works, skip this.

**Step 1 — Check that Python 3 is installed.**

Open Terminal (Spotlight → type "Terminal") and run:

```
python3 --version
```

If you see `Python 3.x.x`, you're good. If you get "command not found",
install Python from [python.org/downloads](https://www.python.org/downloads/)
and reopen Terminal.

**Step 2 — Navigate to the project folder.**

```
cd path/to/Bio-news-mvp
```

Replace `path/to/Bio-news-mvp` with the actual location, for example:

```
cd ~/Downloads/Bio-news-mvp
```

**Step 3 — Create the virtual environment and install dependencies.**

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**Step 4 — Make the launch script executable (one time only).**

```
chmod +x launch_macos.sh
```

**Step 5 — Launch the app.**

```
./launch_macos.sh
```

Or double-click `launch_macos.sh` in Finder (right-click → Open With →
Terminal if it doesn't open automatically).

---

## Running the Tests

Open a terminal in the project folder, then run:

**Windows:**
```
.venv\Scripts\python.exe -m pytest tests\ -m "not integration" -v
```

**Mac / Linux:**
```
.venv/bin/python3 -m pytest tests/ -m "not integration" -v
```

Expected output: **124 passed** (unit tests, no network required).

To also run live network tests (requires internet):

**Windows:**
```
.venv\Scripts\python.exe -m pytest tests\test_integration.py -v
```

**Mac / Linux:**
```
.venv/bin/python3 -m pytest tests/test_integration.py -v
```

Expected output: **10 passed** (real RSS feeds).

---

## Stopping the App

Close the launcher window, or press `Ctrl+C` inside it.
The browser tab will remain open but will show "connection refused"
until the server is restarted.

---

## Project Structure (Reference)

```
Bio-news-mvp/
  Launch BioNews.bat   <- double-click to start (Windows)
  launch_macos.sh      <- double-click to start (Mac)
  launch.py            <- launcher logic (auto-opens browser, cross-platform)
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
