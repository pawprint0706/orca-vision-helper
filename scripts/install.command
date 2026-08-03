#!/usr/bin/env bash
# Install orca-vision-helper (macOS / Linux).
# macOS: double-click this .command file in Finder, or run: bash install.command
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 was not found."
    echo "Install Python 3.11+ (macOS: 'brew install python@3.11'), then run this script again."
    exit 1
fi
if ! python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "Python 3.11+ is required, found $(python3 --version). Upgrade Python and retry."
    exit 1
fi

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Installing orca-vision-helper..."
./.venv/bin/python -m pip install -e . -q
./.venv/bin/python -c "import orca_vision_helper; print('Installed version:', orca_vision_helper.__version__)"

echo ""
read -r -p "Choose your default provider and model now? [Y/n]: " SETUP
case "$SETUP" in
    n|N|no|NO) echo "Skipped. Configure anytime with: ./.venv/bin/orca-vision-helper setup" ;;
    *)
        echo "Running setup — pick a provider, model, and key..."
        ./.venv/bin/orca-vision-helper setup
        ;;
esac

echo ""
echo "Done. Next steps:"
echo "  ./.venv/bin/orca-vision-helper analyze shot.png"
