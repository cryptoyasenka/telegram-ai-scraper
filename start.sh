#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Create venv if missing
if [ ! -f ".venv/bin/python" ]; then
    echo "[*] First run — setting up..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e . >/dev/null 2>&1
    echo "[+] Installed!"
    echo ""
    echo "    Next step: run 'tgp auth' to connect your Telegram account."
    echo "    Then restart this script."
    echo ""
    exit 0
fi

source .venv/bin/activate

# Open browser after 2 seconds (works on macOS and Linux)
(sleep 2 && (open http://127.0.0.1:8765 2>/dev/null || xdg-open http://127.0.0.1:8765 2>/dev/null)) &

echo "[*] TG Parser → http://127.0.0.1:8765"
echo "    Press Ctrl+C to stop"
echo ""
tgp serve
