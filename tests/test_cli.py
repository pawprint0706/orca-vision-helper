"""CLI setup wizard behavior (regression: --set-default flag absent on setup)."""

from __future__ import annotations

import argparse

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


def test_provider_without_subcommand_prints_help(capsys):
    rc = cli.main(["provider"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "add" in out and "list" in out and "remove" in out
