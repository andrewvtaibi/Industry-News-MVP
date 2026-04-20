# launch.py
# Self-contained launcher for the BioNews webapp.
#
# What it does:
#   1. Sets the working directory to the project root (safe regardless of
#      how the script was invoked — shortcut, Explorer, taskbar, etc.)
#   2. Starts uvicorn WITHOUT --reload so OneDrive sync cannot interfere
#   3. Polls the health endpoint until the server is ready
#   4. Opens http://localhost:8000 in the default browser automatically
#   5. Writes logs/launch.log so any startup error is readable in Notepad
#
# The user never needs to touch a terminal — double-click Launch BioNews.bat.

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
import urllib.request
import urllib.error
import logging
import signal
from pathlib import Path

# ---------------------------------------------------------------------------
# Always run from the project root, regardless of invocation context
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Logging — write to logs/launch.log AND print to console
# ---------------------------------------------------------------------------
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "launch.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8", mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("launcher")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HOST     = "127.0.0.1"
PORT     = 8000
URL      = f"http://localhost:{PORT}"
HEALTH   = f"http://{HOST}:{PORT}/api/health"
MAX_WAIT = 30   # seconds to wait for server to be ready
POLL_INT = 0.5  # seconds between health-check polls

# Venv layout differs by OS:
#   Windows  ->  .venv/Scripts/python.exe
#   Mac/Linux -> .venv/bin/python3
if sys.platform == "win32":
    VENV_PY = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    _SETUP_HINT = (
        "    python -m venv .venv\n"
        "    .venv\\Scripts\\python.exe -m pip install -r requirements.txt"
    )
else:
    VENV_PY = PROJECT_ROOT / ".venv" / "bin" / "python3"
    _SETUP_HINT = (
        "    python3 -m venv .venv\n"
        "    .venv/bin/pip install -r requirements.txt"
    )


def _find_python() -> Path:
    """
    Return the venv Python executable.
    Raises SystemExit with a clear message if not found.
    """
    if VENV_PY.exists():
        return VENV_PY
    log.error(
        "Virtual environment not found at: %s\n"
        "Please run the following commands once in a terminal:\n%s",
        VENV_PY,
        _SETUP_HINT,
    )
    input("\nPress Enter to close...")
    sys.exit(1)


def _wait_for_server(timeout: int) -> bool:
    """
    Poll the health endpoint until it responds 200 or timeout expires.
    Returns True if ready, False if timed out.
    """
    deadline = time.monotonic() + timeout
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            with urllib.request.urlopen(HEALTH, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        if attempt == 1:
            log.info("Waiting for server to start...")
        time.sleep(POLL_INT)
    return False


def main() -> None:
    python = _find_python()

    log.info("=" * 55)
    log.info("  BioNews — Company Reports and Information Engine")
    log.info("=" * 55)
    log.info("Project root : %s", PROJECT_ROOT)
    log.info("Python       : %s", python)
    log.info("URL          : %s", URL)
    log.info("")

    # Start uvicorn as a child process.
    # --reload is intentionally OMITTED: it conflicts with OneDrive sync
    # because the file-system watcher sees OneDrive's continuous metadata
    # updates and restarts the server in a loop before it can bind.
    cmd = [
        str(python), "-m", "uvicorn",
        "server.main:app",
        "--host", HOST,
        "--port", str(PORT),
    ]

    log.info("Starting server (this takes a few seconds)...")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        log.error("Failed to launch uvicorn: %s", exc)
        input("\nPress Enter to close...")
        sys.exit(1)

    # Stream server output to the log in a background thread
    import threading

    def _stream_output():
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                log.info("[server] %s", line)

    t = threading.Thread(target=_stream_output, daemon=True)
    t.start()

    # Wait for the server to be ready
    ready = _wait_for_server(MAX_WAIT)

    if not ready:
        log.error(
            "Server did not start within %ds.\n"
            "Check %s for details.",
            MAX_WAIT, LOG_FILE,
        )
        proc.terminate()
        input("\nPress Enter to close...")
        sys.exit(1)

    log.info("")
    log.info("Server is ready!")
    log.info("Opening browser at %s", URL)
    log.info("")
    log.info("Press Ctrl+C (or close this window) to stop the server.")
    log.info("")

    webbrowser.open(URL)

    # Keep running until user closes window or presses Ctrl+C
    def _shutdown(signum, frame):
        log.info("Shutting down...")
        proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        proc.wait()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        proc.terminate()


if __name__ == "__main__":
    main()
