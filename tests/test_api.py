"""Vision backends: request shape, browser UA, error mapping, staged fallback."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from orca_vision_helper import api
from orca_vision_helper.api import (
    AnthropicBackend,
    BaseBackend,
    OllamaBackend,
    OpenAICompatibleBackend,
)
from orca_vision_helper.errors import VisionError, VisionErrorCode
from orca_vision_helper.models import ProviderConfig


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))


class _Resp:
    def __init__(self, payload, status=200, text="", headers=None):
        self._payload = payload
        self.status_code = status
        self.text = text
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err", request=httpx.Request("POST", "http://x"), response=self
            )

    def json(self):
        return self._payload


def _make_png(tmp_path: Path, size=(10, 10)) -> Path:
    from PIL import Image

    p = tmp_path / "shot.png"
    Image.new("RGB", size, (100, 100, 100)).save(p)
    return p


# --------------------------------------------------------------------------- #
# OpenAI-compatible backend
# --------------------------------------------------------------------------- #
def _openai_provider(provider_type="opencode-go"):
    return ProviderConfig(id=provider_type, type=provider_type, model="qwen3.6-plus")


def test_openai_request_shape(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(url=url, body=json, headers=headers, timeout=timeout)
        return _Resp({"choices": [{"message": {"content": '{"summary":"s","issues":[]}'}}]})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    out = OpenAICompatibleBackend(_openai_provider(), "sk-test",
                                  base_url="https://opencode.ai/zen/go/v1")._complete(
        b"img", "image/png", "prompt"
    )

    assert captured["url"] == "https://opencode.ai/zen/go/v1/chat/completions"
    assert captured["body"]["model"] == "qwen3.6-plus"
    assert captured["body"]["max_tokens"] == 2048
    content = captured["body"]["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["headers"]["User-Agent"].startswith("Mozilla/5.0")
    assert captured["timeout"] == 120.0
    assert out == '{"summary":"s","issues":[]}'


def test_openai_browser_ua_mandatory(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _Resp({"choices": [{"message": {"content": "x"}}]})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    OpenAICompatibleBackend(_openai_provider(), "k", base_url="http://b")._complete(
        b"i", "image/png", "p"
    )
    assert "Mozilla/5.0" in captured["headers"]["User-Agent"]


def test_custom_without_key_sends_no_auth_header(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _Resp({"choices": [{"message": {"content": "x"}}]})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    be = OpenAICompatibleBackend(
        ProviderConfig(id="mygw", type="custom", model="m"), None, base_url="http://gw"
    )
    assert be._complete(b"i", "image/png", "p") == "x"
    assert "Authorization" not in captured["headers"]


def test_missing_key_cloud_provider_raises(monkeypatch):
    be = OpenAICompatibleBackend(_openai_provider(), None,
                                 base_url="https://opencode.ai/zen/go/v1")
    with pytest.raises(VisionError) as ei:
        be._complete(b"i", "image/png", "p")
    assert ei.value.code == VisionErrorCode.AUTH_FAILED


def test_custom_requires_base_url():
    with pytest.raises(VisionError) as ei:
        OpenAICompatibleBackend(ProviderConfig(id="c", type="custom"), "k", base_url=None)
    assert ei.value.code == VisionErrorCode.BAD_REQUEST


# --------------------------------------------------------------------------- #
# Anthropic backend
# --------------------------------------------------------------------------- #
def test_anthropic_request_shape(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(url=url, body=json, headers=headers, timeout=timeout)
        return _Resp({"content": [{"type": "text", "text": '{"summary":"s"}'}]})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    be = AnthropicBackend(ProviderConfig(id="anthropic", type="anthropic"), "sk-ant")
    out = be._complete(b"img", "image/png", "prompt")

    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "sk-ant"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert "Mozilla/5.0" in captured["headers"]["User-Agent"]
    src = captured["body"]["messages"][0]["content"][0]["source"]
    assert src["type"] == "base64" and src["media_type"] == "image/png"
    assert out == '{"summary":"s"}'


def test_anthropic_refusal_maps_to_content_filtered(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return _Resp({"stop_reason": "refusal", "content": []})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    be = AnthropicBackend(ProviderConfig(id="anthropic", type="anthropic"), "k")
    with pytest.raises(VisionError) as ei:
        be._complete(b"i", "image/png", "p")
    assert ei.value.code == VisionErrorCode.CONTENT_FILTERED


# --------------------------------------------------------------------------- #
# Ollama backend
# --------------------------------------------------------------------------- #
def _ollama_backend():
    return OllamaBackend(
        ProviderConfig(id="ollama", type="ollama", model="qwen3-vl:4b"),
        host="http://localhost:11434",
    )


def test_ollama_request_disables_thinking(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["body"] = json
        return _Resp({"message": {"content": '{"summary":"ok","issues":[]}'}})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    out = _ollama_backend()._complete(b"img", "image/png", "prompt")

    assert captured["body"]["think"] is False
    assert captured["body"]["format"] == "json"
    assert captured["body"]["messages"][0]["images"] == ["aW1n"]
    assert out == '{"summary":"ok","issues":[]}'


def test_ollama_falls_back_to_thinking_text(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return _Resp({"message": {"content": "", "thinking": "reasoning text"}})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    assert _ollama_backend()._complete(b"img", "image/png", "p") == "reasoning text"


def test_ollama_empty_response_raises(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return _Resp({"message": {"content": "", "thinking": ""}})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    with pytest.raises(VisionError) as ei:
        _ollama_backend()._complete(b"img", "image/png", "p")
    assert ei.value.code == VisionErrorCode.RESPONSE_INVALID


def test_ollama_think_unsupported_retries_without_think(monkeypatch):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json)
        if "think" in json:
            return _Resp({}, status=400, text="bad request")
        return _Resp({"message": {"content": '{"summary":"s","issues":[]}'}})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    out = _ollama_backend()._complete(b"img", "image/png", "p")

    assert len(calls) == 2
    assert "think" not in calls[1]
    assert out == '{"summary":"s","issues":[]}'


def test_ollama_persistent_400_surfaces_error(monkeypatch):
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json)
        return _Resp({}, status=400, text="invalid image")

    monkeypatch.setattr(api.httpx, "post", fake_post)
    with pytest.raises(VisionError) as ei:
        _ollama_backend()._complete(b"img", "image/png", "p")
    assert len(calls) == 2
    assert ei.value.code == VisionErrorCode.BAD_REQUEST


def test_ollama_connect_error_maps(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        raise httpx.ConnectError("refused", request=httpx.Request("POST", "http://x"))

    monkeypatch.setattr(api.httpx, "post", fake_post)
    with pytest.raises(VisionError) as ei:
        _ollama_backend()._complete(b"img", "image/png", "p")
    assert ei.value.code == VisionErrorCode.OLLAMA_UNAVAILABLE


def test_ollama_model_404_maps(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return _Resp({}, status=404, text="model not found")

    monkeypatch.setattr(api.httpx, "post", fake_post)
    with pytest.raises(VisionError) as ei:
        _ollama_backend()._complete(b"img", "image/png", "p")
    assert ei.value.code == VisionErrorCode.OLLAMA_UNAVAILABLE


# --------------------------------------------------------------------------- #
# HTTP error mapping (plan §4.2)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, VisionErrorCode.BAD_REQUEST),
        (401, VisionErrorCode.AUTH_FAILED),
        (402, VisionErrorCode.QUOTA_EXCEEDED),
        (403, VisionErrorCode.AUTH_FAILED),
        (404, VisionErrorCode.MODEL_NOT_FOUND),
        (413, VisionErrorCode.BAD_REQUEST),
        (422, VisionErrorCode.BAD_REQUEST),
        (429, VisionErrorCode.RATE_LIMIT),
        (500, VisionErrorCode.SERVER_ERROR),
        (503, VisionErrorCode.SERVER_ERROR),
    ],
)
def test_status_mapping(monkeypatch, status, expected):
    def fake_post(url, json=None, headers=None, timeout=None):
        return _Resp({}, status=status)

    monkeypatch.setattr(api.httpx, "post", fake_post)
    be = OpenAICompatibleBackend(_openai_provider(), "k", base_url="http://b")
    with pytest.raises(VisionError) as ei:
        be._complete(b"i", "image/png", "p")
    assert ei.value.code == expected
    assert ei.value.http_status == status


def test_retry_after_parsed(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return _Resp({}, status=429, headers={"retry-after": "17"})

    monkeypatch.setattr(api.httpx, "post", fake_post)
    be = OpenAICompatibleBackend(_openai_provider(), "k", base_url="http://b")
    with pytest.raises(VisionError) as ei:
        be._complete(b"i", "image/png", "p")
    assert ei.value.retry_after_sec == 17.0


def test_timeout_maps_to_timeout(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        raise httpx.TimeoutException("took too long")

    monkeypatch.setattr(api.httpx, "post", fake_post)
    be = OpenAICompatibleBackend(_openai_provider(), "k", base_url="http://b")
    with pytest.raises(VisionError) as ei:
        be._complete(b"i", "image/png", "p")
    assert ei.value.code == VisionErrorCode.TIMEOUT


def test_network_error_maps(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        raise httpx.ConnectError("refused", request=httpx.Request("POST", "http://x"))

    monkeypatch.setattr(api.httpx, "post", fake_post)
    be = OpenAICompatibleBackend(_openai_provider(), "k", base_url="http://b")
    with pytest.raises(VisionError) as ei:
        be._complete(b"i", "image/png", "p")
    assert ei.value.code == VisionErrorCode.NETWORK


# --------------------------------------------------------------------------- #
# staged fallback in BaseBackend.analyze (plan §7.7)
# --------------------------------------------------------------------------- #
class _FakeBackend(BaseBackend):
    def __init__(self, replies, provider=None):
        super().__init__(provider or ProviderConfig(id="fake", type="ollama", model="x"))
        self._replies = list(replies)
        self.calls = 0

    def _complete(self, image_bytes, mime, prompt):
        self.calls += 1
        return self._replies.pop(0)


def test_corrective_retry_recovers(tmp_path):
    src = _make_png(tmp_path)
    be = _FakeBackend(["설명만 있는 응답", '{"summary":"recovered","issues":[]}'])
    report = be.analyze(src, "prompt")
    assert be.calls == 2
    assert report.summary == "recovered"
    assert report.parse_degraded is False


def test_falls_back_to_degraded(tmp_path):
    src = _make_png(tmp_path)
    be = _FakeBackend(["prose one", "prose two"])
    report = be.analyze(src, "prompt")
    assert be.calls == 2
    assert report.parse_degraded is True
    assert report.raw_text == "prose two"


def test_corrective_retry_error_keeps_first_raw(tmp_path):
    src = _make_png(tmp_path)

    class _FailRetry(_FakeBackend):
        def _complete(self, image_bytes, mime, prompt):
            self.calls += 1
            if self.calls > 1:
                raise VisionError(VisionErrorCode.SERVER_ERROR, "boom")
            return "prose one"

    report = _FailRetry([]).analyze(src, "prompt")
    assert report.parse_degraded is True
    assert report.raw_text == "prose one"


def test_no_schema_skips_corrective_retry(tmp_path):
    src = _make_png(tmp_path)
    be = _FakeBackend(["자유 형식 응답, JSON 아님"])
    report = be.analyze(src, "my prompt", schema=False)
    assert be.calls == 1
    assert report.parse_degraded is True
    assert report.raw_text == "자유 형식 응답, JSON 아님"


def test_missing_image_raises_bad_request(tmp_path):
    be = _FakeBackend([])
    with pytest.raises(VisionError) as ei:
        be.analyze(tmp_path / "nope.png", "prompt")
    assert ei.value.code == VisionErrorCode.BAD_REQUEST
