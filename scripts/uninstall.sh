#!/usr/bin/env bash
# Uninstall orca-vision-helper (macOS / Linux).
# macOS: double-click this .command file in Finder, or run: bash uninstall.command
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -x ./.venv/bin/orca-vision-helper ]; then
    echo "Removing registered providers (and their keychain keys)..."
    ./.venv/bin/python scripts/remove_providers.py
fi

echo "Deleting configuration..."
rm -rf "$HOME/.config/orca-vision-helper"

echo "Removing the global command (if any)..."
for TARGET in /usr/local/bin "$HOME/.local/bin"; do
    if [ -L "$TARGET/orca-vision-helper" ]; then
        rm -f "$TARGET/orca-vision-helper"
        echo "Removed: $TARGET/orca-vision-helper"
    fi
done

echo "Deleting the virtual environment..."
rm -rf .venv

echo ""
echo "Uninstalled."
echo "If provider keys could not be removed, delete them manually from"
echo "Keychain Access (entries under service \"orca-vision-helper\")."
echo "If a legacy/vision-limited agent awareness rule exists, remove only the block between the"
echo "BEGIN/END orca-vision-helper markers; preserve all other instructions."
echo "See docs/AGENT_UNINSTALL.md for details."
