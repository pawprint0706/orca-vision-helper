"""Config persistence + provider registry helpers (plan §7.3)."""

from __future__ import annotations

import json

import pytest

from orca_vision_helper import config as cfg
from orca_vision_helper.errors import VisionError, VisionErrorCode
from orca_vision_helper.models import ProviderConfig


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))


def _provider(pid="opencode-go", ptype="opencode-go"):
    return ProviderConfig(id=pid, type=ptype, model="qwen3.6-plus",
                          base_url="https://opencode.ai/zen/go/v1")


def test_first_provider_becomes_default():
    c = cfg.AppConfig()
    c.add_provider(_provider())
    assert c.default_provider_id == "opencode-go"


def test_duplicate_provider_raises():
    c = cfg.AppConfig()
    c.add_provider(_provider())
    with pytest.raises(ValueError):
        c.add_provider(_provider())


def test_remove_provider_resets_default():
    c = cfg.AppConfig()
    c.add_provider(_provider())
    c.add_provider(_provider("ollama", "ollama"))
    c.set_default_provider("ollama")
    c.remove_provider("ollama")
    assert c.default_provider_id == "opencode-go"
    assert c.last_used_provider_id is None


def test_mark_used_promotes_default():
    c = cfg.AppConfig()
    c.add_provider(_provider())
    c.add_provider(_provider("openrouter", "openrouter"))
    c.mark_used("openrouter")
    assert c.effective_default().id == "openrouter"


def test_effective_default_last_used_wins():
    c = cfg.AppConfig()
    c.add_provider(_provider())
    c.add_provider(_provider("openai", "openai"))
    c.set_default_provider("opencode-go")
    c.mark_used("openai")
    assert c.effective_default().id == "openai"


def test_set_default_pins_last_used():
    c = cfg.AppConfig()
    c.add_provider(_provider())
    c.add_provider(_provider("openai", "openai"))
    c.mark_used("openai")
    c.set_default_provider("opencode-go")
    assert c.effective_default().id == "opencode-go"


def test_set_default_unknown_returns_false():
    c = cfg.AppConfig()
    assert c.set_default_provider("nope") is False


def test_roundtrip_persists(tmp_path):
    cfg.update_config(lambda latest: latest.add_provider(_provider()))
    cfg.update_config(lambda latest: latest.mark_used("opencode-go"))
    loaded = cfg.load_config()
    assert len(loaded.providers) == 1
    assert loaded.providers[0].type == "opencode-go"
    assert loaded.default_provider_id == "opencode-go"
    assert loaded.last_used_provider_id == "opencode-go"


def test_config_path_uses_xdg():
    assert str(cfg.config_dir()).endswith("orca-vision-helper")
    assert cfg.config_path().name == "config.json"


def test_corrupt_config_is_rejected_without_overwrite(tmp_path):
    cfg.config_path().parent.mkdir(parents=True, exist_ok=True)
    cfg.config_path().write_text("{not json!!")
    with pytest.raises(VisionError) as exc_info:
        cfg.load_config()
    assert exc_info.value.code == VisionErrorCode.BAD_REQUEST
    assert cfg.config_path().read_text() == "{not json!!"


def test_schema_invalid_config_is_rejected_without_overwrite(tmp_path):
    cfg.config_path().parent.mkdir(parents=True, exist_ok=True)
    raw = '{"providers":[{"id":"x","type":"not-a-provider"}]}'
    cfg.config_path().write_text(raw)
    with pytest.raises(VisionError) as exc_info:
        cfg.load_config()
    assert exc_info.value.code == VisionErrorCode.BAD_REQUEST
    assert cfg.config_path().read_text() == raw


def test_no_key_in_config(tmp_path):
    # Keys must never be persisted — key_ref only.
    cfg.update_config(lambda latest: latest.add_provider(_provider()))
    raw = json.loads(cfg.config_path().read_text())
    assert "key" not in raw
    assert raw["providers"][0].get("key_ref") is None
