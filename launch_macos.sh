#!/usr/bin/env bash
# launch_macos.sh
# Double-click this file (or run it in Terminal) to start BioNews on Mac.
# The browser opens automatically. Keep this window open while using the app.
#
# First-time setup (run once in Terminal before using this script):
#   python3 -m venv .venv
#   .venv/bin/pip install -r requirements.txt

# Move to the folder containing this script, regardless of how it was invoked
cd "$(dirname "$0")" || exit 1

echo ""
echo "  Starting BioNews..."
echo "  The browser will open automatically in a few seconds."
echo "  Keep this window open while using the app."
echo "  Press Ctrl+C to stop the server."
echo ""

python3 launch.py

echo ""
echo "  BioNews has stopped."
read -rp "Press Enter to close..."
