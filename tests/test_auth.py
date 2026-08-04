"""API-key resolution order (plan §5.5): env -> auth.json -> keyring."""

from __future__ import annotations

import json

import pytest

from orca_vision_helper import auth
from orca_vision_helper.models import ProviderConfig


class _FakeKeyring:
    def __init__(self):
        self._store = {}

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def get_password(self, service, username):
        return self._store.get((service, username))

    def delete_password(self, service, username):
        self._store.pop((service, username), None)


@pytest.fixture()
def fake_keyring(monkeypatch):
    kr = _FakeKeyring()
    monkeypatch.setattr(auth, "_keyring", lambda: kr)
    return kr


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("OPENCODE_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def _opencode_provider(provider_type="opencode-go"):
    return ProviderConfig(id=provider_type, type=provider_type, model="qwen3.6-plus")


def test_opencode_env_wins(monkeypatch, fake_keyring):
    monkeypatch.setenv("OPENCODE_API_KEY", "env-key")
    fake_keyring.set_password(auth.SERVICE, auth.keyref_for("opencode-go"), "ring-key")
    assert auth.resolve_key(_opencode_provider()) == "env-key"


def test_opencode_auth_json_fallback(monkeypatch, tmp_path):
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(
        json.dumps({"opencode-go": {"type": "api", "key": "go-key"},
                    "opencode": {"type": "api", "key": "zen-key"}})
    )
    monkeypatch.setattr(auth, "OPCODE_AUTH_PATH", auth_file)
    assert auth.resolve_key(_opencode_provider("opencode-go")) == "go-key"
    assert auth.resolve_key(_opencode_provider("opencode")) == "zen-key"


def test_opencode_auth_json_cross_fallback(monkeypatch, tmp_path):
    # Only the opencode-go entry exists — opencode type falls back to it.
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps({"opencode-go": {"type": "api", "key": "go-key"}}))
    monkeypatch.setattr(auth, "OPCODE_AUTH_PATH", auth_file)
    assert auth.resolve_key(_opencode_provider("opencode")) == "go-key"


def test_opencode_keyring_last_resort(fake_keyring, monkeypatch, tmp_path):
    # Point auth.json away so the real ~/.local/share/opencode/auth.json can't leak in.
    monkeypatch.setattr(auth, "OPCODE_AUTH_PATH", tmp_path / "missing.json")
    fake_keyring.set_password(auth.SERVICE, "provider:opencode-go", "ring-key")
    provider = _opencode_provider("opencode-go")
    provider.key_ref = auth.keyref_for("opencode-go")
    assert auth.resolve_key(provider) == "ring-key"


def test_opencode_nothing_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(auth, "OPCODE_AUTH_PATH", tmp_path / "missing.json")
    assert auth.resolve_key(_opencode_provider()) is None


@pytest.mark.parametrize(
    ("provider_type", "env_var"),
    [("openrouter", "OPENROUTER_API_KEY"),
     ("anthropic", "ANTHROPIC_API_KEY"),
     ("openai", "OPENAI_API_KEY")],
)
def test_cloud_env_var(monkeypatch, provider_type, env_var):
    monkeypatch.setenv(env_var, "env-key")
    p = ProviderConfig(id=provider_type, type=provider_type)
    assert auth.resolve_key(p) == "env-key"


def test_cloud_keyring_after_env(monkeypatch, fake_keyring):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    fake_keyring.set_password(auth.SERVICE, "provider:anthropic", "ring-key")
    p = ProviderConfig(id="anthropic", type="anthropic", key_ref="provider:anthropic")
    assert auth.resolve_key(p) == "env-key"


def test_cloud_keyring_fallback(fake_keyring):
    fake_keyring.set_password(auth.SERVICE, "provider:anthropic", "ring-key")
    p = ProviderConfig(id="anthropic", type="anthropic", key_ref="provider:anthropic")
    assert auth.resolve_key(p) == "ring-key"


def test_custom_keyring_only(fake_keyring):
    fake_keyring.set_password(auth.SERVICE, "provider:mygw", "ring-key")
    p = ProviderConfig(id="mygw", type="custom", key_ref="provider:mygw")
    assert auth.resolve_key(p) == "ring-key"


def test_custom_no_env_fallback(monkeypatch):
    # custom has no conventional env var — nothing should resolve without keyring.
    monkeypatch.setenv("OPENAI_API_KEY", "unrelated")
    assert auth.resolve_key(ProviderConfig(id="mygw", type="custom")) is None


def test_ollama_always_none():
    assert auth.resolve_key(ProviderConfig(id="ollama", type="ollama")) is None


def test_has_key_is_literal_for_local_provider():
    assert auth.has_key(ProviderConfig(id="ollama", type="ollama")) is False


def test_delete_key_missing_is_safe(fake_keyring):
    auth.delete_key("provider:never-existed")  # must not raise
