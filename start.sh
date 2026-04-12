#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Find python command
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "[!] Python not found. Install Python 3.11+ first."
    exit 1
fi

# Create venv if missing
if [ ! -f ".venv/bin/activate" ]; then
    echo "[*] Creating virtual environment..."
    $PYTHON -m venv .venv
    source .venv/bin/activate
    echo "[*] Installing dependencies (this may take a minute)..."
    pip install -e .
    echo "[+] Installed successfully!"
else
    source .venv/bin/activate
fi

# Check if auth is needed
if [ ! -f "data/session.session" ]; then
    echo ""
    echo "============================================"
    echo "  First time setup: Telegram authentication"
    echo "============================================"
    echo ""
    echo "  1. Go to https://my.telegram.org"
    echo "  2. Get your API ID and API Hash"
    echo "  3. Enter them below:"
    echo ""
    tgp auth
fi

# Open browser after 2 seconds (works on macOS and Linux)
(sleep 2 && (open http://127.0.0.1:8765 2>/dev/null || xdg-open http://127.0.0.1:8765 2>/dev/null)) &

echo ""
echo "[*] TG Parser: http://127.0.0.1:8765"
echo "    Press Ctrl+C to stop the server."
echo ""
tgp serve
