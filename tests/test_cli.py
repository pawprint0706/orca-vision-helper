"""CLI setup wizard behavior (regression: --set-default flag absent on setup)."""

from __future__ import annotations

import argparse
import io
import sys

import httpx
import pytest

from orca_vision_helper import cli
from orca_vision_helper import config as cfg
from orca_vision_helper.models import ProviderConfig


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))


def _seed_provider() -> None:
    cfg.update_config(
        lambda latest: latest.add_provider(
            ProviderConfig(
                id="opencode-go",
                type="opencode-go",
                model="qwen3.6-plus",
                base_url="https://opencode.ai/zen/go/v1",
            )
        )
    )


def _run_setup(monkeypatch, answers: list[str]):
    monkeypatch.setattr("builtins.input", lambda prompt="": answers.pop(0))
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": answers.pop(0))
    # Namespace without set_default — reproduces the original crash
    return cli._cmd_setup(argparse.Namespace())


def test_setup_on_empty_config_creates_default(monkeypatch):
    rc = _run_setup(monkeypatch, ["1", "", ""])
    assert rc == 0
    config = cfg.load_config()
    assert config.default_provider_id == "opencode-go"
    assert config.providers[0].model == "qwen3.6-plus"


def test_setup_on_existing_default_updates_without_crashing(monkeypatch):
    _seed_provider()
    # answer: same provider, new model, no key
    rc = _run_setup(monkeypatch, ["1", "qwen3.7-plus", ""])
    assert rc == 0
    config = cfg.load_config()
    assert len(config.providers) == 1
    assert config.providers[0].model == "qwen3.7-plus"
    assert config.default_provider_id == "opencode-go"


def test_setup_invalid_choice_returns_1(monkeypatch):
    rc = _run_setup(monkeypatch, ["99"])
    assert rc == 1
    assert cfg.load_config().providers == []


def test_setup_custom_accepts_optional_key(monkeypatch):
    stored = {}
    monkeypatch.setattr(
        cli.auth,
        "set_key",
        lambda ref, key: stored.update(ref=ref, key=key),
    )

    rc = _run_setup(
        monkeypatch,
        ["7", "https://gateway.example/v1", "vision-model", "gateway-key"],
    )

    assert rc == 0
    provider = cfg.load_config().get_provider("custom")
    assert provider.key_ref == cli.auth.keyref_for("custom")
    assert stored == {"ref": "provider:custom", "key": "gateway-key"}


def test_setup_custom_allows_keyless_gateway(monkeypatch):
    rc = _run_setup(
        monkeypatch,
        ["7", "http://localhost:8080/v1", "vision-model", ""],
    )

    assert rc == 0
    assert cfg.load_config().get_provider("custom").key_ref is None


def test_provider_without_subcommand_prints_help(capsys):
    rc = cli.main(["provider"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "add" in out and "list" in out and "remove" in out


def test_force_utf8_stdio(monkeypatch):
    out_buf = io.BytesIO()
    out = io.TextIOWrapper(out_buf, encoding="ascii", errors="strict")
    err = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
    in_buf = io.BytesIO("가나다".encode())
    stdin = io.TextIOWrapper(in_buf, encoding="ascii", errors="strict")
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    monkeypatch.setattr(sys, "stdin", stdin)
    cli._force_utf8_stdio()
    assert out.encoding.replace("-", "").lower() == "utf8"
    print("가나다")
    out.flush()
    assert "가나다".encode() in out_buf.getvalue()


def test_provider_type_change_resets_type_defaults(capsys):
    _seed_provider()
    rc = cli.main(["provider", "update", "opencode-go", "--type", "anthropic"])
    assert rc == 0
    provider = cfg.load_config().get_provider("opencode-go")
    assert provider.type == "anthropic"
    assert provider.model == "claude-sonnet-4-6"
    assert provider.base_url == "https://api.anthropic.com/v1/messages"


def test_provider_type_change_allows_explicit_overrides(capsys):
    _seed_provider()
    rc = cli.main([
        "provider", "update", "opencode-go", "--type", "ollama",
        "--model", "qwen3-vl:4b", "--base-url", "http://ollama.internal:11434",
    ])
    assert rc == 0
    provider = cfg.load_config().get_provider("opencode-go")
    assert provider.model == "qwen3-vl:4b"
    assert provider.base_url == "http://ollama.internal:11434"


def test_change_to_custom_requires_url_and_model(capsys):
    _seed_provider()
    rc = cli.main(["provider", "update", "opencode-go", "--type", "custom"])
    assert rc == 1
    assert cfg.load_config().get_provider("opencode-go").type == "opencode-go"


def test_anthropic_probe_uses_models_url_and_rejects_unauthorized(monkeypatch):
    captured = {}

    class Response:
        status_code = 401

        def json(self):
            return {"error": "unauthorized"}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return Response()

    monkeypatch.setattr(httpx, "get", fake_get)
    provider = ProviderConfig(
        id="anthropic", type="anthropic", model="m",
        base_url="https://api.anthropic.com/v1/messages",
    )
    result = cli._probe_endpoint(provider, "bad-key")
    assert captured["url"] == "https://api.anthropic.com/v1/models"
    assert result["reachable"] is True
    assert result["authentication_valid"] is False
    assert result["ok"] is False


def test_probe_fails_when_configured_model_is_not_listed(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {"data": [{"id": "different-model"}]}

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: Response())
    provider = ProviderConfig(
        id="custom", type="custom", model="wanted", base_url="http://local/v1"
    )
    result = cli._probe_endpoint(provider, None)
    assert result["authentication_valid"] is True
    assert result["model_available"] is False
    assert result["ok"] is False


def test_cli_reports_invalid_config_as_structured_json(capsys):
    cfg.config_path().parent.mkdir(parents=True, exist_ok=True)
    cfg.config_path().write_text("{broken", encoding="utf-8")
    rc = cli.main(["provider", "list"])
    output = capsys.readouterr().out
    assert rc == 1
    assert '"error_code": "BAD_REQUEST"' in output
    assert '"status": "error"' in output
