"""API-key resolution (plan §7.6, §5.5).

Keys are NEVER written to config.json. Sources, in order (plan §5.5):

- opencode-go / opencode: `OPENCODE_API_KEY` env -> opencode auth.json
  (`~/.local/share/opencode/auth.json`, "opencode-go" -> "opencode" order)
- openrouter / anthropic / openai: env var -> OS keychain (keyring)
- custom: OS keychain only (env optional, gateways differ)
- ollama: no key (local)

The OS keychain is also checked as a final fallback for every type, so
`--key`-registered providers always work.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import ProviderConfig

SERVICE = "orca-vision-helper"

OPCODE_ENV = "OPENCODE_API_KEY"
OPCODE_AUTH_PATH = Path.home() / ".local/share/opencode/auth.json"


def _keyring():
    """Import keyring lazily so the package imports without it installed."""
    import keyring

    return keyring


def keyref_for(provider_id: str) -> str:
    return f"provider:{provider_id}"


def set_key(key_ref: str, api_key: str) -> None:
    _keyring().set_password(SERVICE, key_ref, api_key)


def delete_key(key_ref: str) -> None:
    # Deleting a non-existent key must not raise (keyring backends vary).
    try:
        _keyring().delete_password(SERVICE, key_ref)
    except Exception:  # noqa: BLE001, S110 — non-fatal backend quirks
        pass


def _opencode_keys() -> dict[str, str]:
    """``{"opencode-go": key, "opencode": key}`` from the opencode auth.json."""
    try:
        data = json.loads(OPCODE_AUTH_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    for name in ("opencode-go", "opencode"):
        entry = data.get(name)
        if isinstance(entry, dict) and entry.get("key"):
            out[name] = entry["key"]
    return out


def resolve_key(provider: ProviderConfig) -> str | None:
    """Resolve the API key for a provider, or None when none is available."""
    if provider.is_local:
        return None

    # 1) conventional env var (plan §5.5)
    if provider.type in ("opencode-go", "opencode"):
        value = os.environ.get(OPCODE_ENV)
        if value:
            return value
    elif provider.type in ("openrouter", "anthropic", "openai"):
        value = os.environ.get(f"{provider.type.upper()}_API_KEY")
        if value:
            return value

    # 2) opencode auth.json fallback ("opencode-go" -> "opencode" order)
    if provider.type in ("opencode-go", "opencode"):
        keys = _opencode_keys()
        value = keys.get(provider.type) or keys.get("opencode-go") or keys.get("opencode")
        if value:
            return value

    # 3) OS keychain (keyring) — explicit --key registrations
    if provider.key_ref:
        try:
            value = _keyring().get_password(SERVICE, provider.key_ref)
        except Exception:  # noqa: BLE001 — keyring backend may be unavailable
            value = None
        if value:
            return value

    return None


def has_key(provider: ProviderConfig) -> bool:
    return provider.is_local or resolve_key(provider) is not None
