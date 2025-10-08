#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

echo "Recreating .venv..."
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

echo "Upgrading pip and installing dev deps..."
python -m pip install --upgrade pip setuptools wheel
if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
else
  pip install pytest responses requests pytest-httpserver pytest-asyncio anyio pycountry cloudscraper mock
fi

# optional editable install
pip install -e . || true

echo "Done. Run: source .venv/bin/activate"
python --version
which python
pip --version
