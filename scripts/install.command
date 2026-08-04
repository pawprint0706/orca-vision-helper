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

CONSENT_MARKER=".venv/.cloud-upload-consent-v1"
RECORD_CLOUD_CONSENT=0
if [ ! -f "$CONSENT_MARKER" ]; then
    echo ""
    echo "Cloud image transmission consent"
    echo "  When you configure a cloud or remote custom provider, images selected"
    echo "  for analysis are uploaded to that external service and may contain"
    echo "  sensitive information. Local Ollama analysis does not upload images."
    read -r -p "Do you understand and consent to install with cloud-provider support? [y/N]: " CLOUD_CONSENT
    case "$CLOUD_CONSENT" in
        y|Y|yes|YES) RECORD_CLOUD_CONSENT=1 ;;
        *)
            echo "Installation cancelled: cloud image transmission consent was not granted."
            exit 1
            ;;
    esac
fi

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Installing orca-vision-helper..."
./.venv/bin/python -m pip install -e . -q
./.venv/bin/python -c "import orca_vision_helper; print('Installed version:', orca_vision_helper.__version__)"
if [ "$RECORD_CLOUD_CONSENT" -eq 1 ]; then
    printf '%s\n' "cloud-upload-consent-v1" > "$CONSENT_MARKER"
fi

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
echo "Registering a global 'orca-vision-helper' command (run from any directory)..."
TARGET=""
if [ -w /usr/local/bin ]; then
    TARGET=/usr/local/bin
elif { [ -d "$HOME/.local/bin" ] || mkdir -p "$HOME/.local/bin" 2>/dev/null; } && [ -w "$HOME/.local/bin" ]; then
    TARGET="$HOME/.local/bin"
fi
if [ -n "$TARGET" ]; then
    ln -sfn "$PWD/.venv/bin/orca-vision-helper" "$TARGET/orca-vision-helper"
    if echo ":$PATH:" | grep -q ":$TARGET:"; then
        echo "Registered: $TARGET/orca-vision-helper (on PATH)"
    else
        echo "Registered: $TARGET/orca-vision-helper"
        echo "NOTE: $TARGET is not on your PATH yet. Add it, e.g. in ~/.zshrc:"
        echo "  export PATH=\"$TARGET:\$PATH\""
    fi
else
    echo "ERROR: No writable bin directory found. Add one to your PATH and re-run:"
    echo "  mkdir -p \"$HOME/.local/bin\" && export PATH=\"$HOME/.local/bin:\$PATH\""
    exit 1
fi

echo ""
echo "Recommended: make AI agents aware of this tool (so they can 'see' screenshots)."
echo "With your approval, copy the marked block from docs/AGENT_TOOL_RULE.md"
echo "into your harness's global instructions. Do NOT copy the root AGENTS.md."
echo "If the marked block already exists, replace only that block; do not append"
echo "a duplicate or overwrite unrelated instructions."
echo "See docs/AGENT_INSTALL.md for target paths and the safe merge procedure."

echo ""
echo "Done. Next steps:"
echo "  ./.venv/bin/orca-vision-helper analyze shot.png"
