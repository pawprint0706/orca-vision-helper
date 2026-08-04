"""Installer consent contract and cross-platform parity."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONSENT_MARKER = ".cloud-upload-consent-v1"


def test_posix_installers_are_identical_and_default_deny():
    shell = (ROOT / "scripts/install.sh").read_text(encoding="utf-8")
    command = (ROOT / "scripts/install.command").read_text(encoding="utf-8")
    assert shell == command
    assert CONSENT_MARKER in shell
    assert "[y/N]" in shell
    assert "cloud image transmission consent was not granted" in shell
    assert shell.index("Cloud image transmission consent") < shell.index(
        'echo "Creating virtual environment..."'
    )
    assert shell.index("pip install -e .") < shell.index(
        'printf \'%s\\n\' "cloud-upload-consent-v1"'
    )


def test_windows_installer_has_same_consent_contract():
    batch = (ROOT / "scripts/install.bat").read_text(encoding="utf-8")
    assert CONSENT_MARKER in batch
    assert "[y/N]" in batch
    assert "cloud image transmission consent was not granted" in batch
    assert batch.index("Cloud image transmission consent") < batch.index(
        "echo Creating virtual environment..."
    )
    assert batch.index("pip install -e .") < batch.index(
        'echo cloud-upload-consent-v1'
    )
