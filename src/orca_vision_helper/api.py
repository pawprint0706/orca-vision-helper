"""Vision backends (plan §4, §5.3).

`build_backend(provider, api_key)` constructs the concrete backend for a
registered provider. OpenAI-compatible endpoints (opencode-go, opencode,
openrouter, openai, custom) share one client differing only by base_url;
anthropic uses the Messages API; ollama talks to the local /api/chat.

Common rules (plan §4.2):
- every request carries a browser-style User-Agent (Cloudflare bot check)
- timeouts: cloud 60s, Ollama 180s
"""

from __future__ import annotations

import base64
from pathlib import Path

import httpx

from . import report as report_mod
from .config import load_config
from .errors import VisionError, VisionErrorCode
from .imaging import preprocess
from .models import ProviderConfig, VisionReportBody
from .providers import CATALOG

# Browser-style UA required to pass the opencode endpoint's Cloudflare bot gate
# (research §3.3); harmless for other providers.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

DEFAULT_PROMPT = (
    "Find overlapping/broken parts, misalignment, and clipped/occluded elements "
    "in this UI, and explain them with the likely CSS/style areas to fix."
)

_MAX_TOKENS = 2048
# 120s cloud timeout: E2E-measured qwen3.6-plus (opencode-go) responses of
# 26–55s with occasional >60s spikes (plan §4.2 originally said 60s; raised).
_CLOUD_TIMEOUT = 120.0
_OLLAMA_TIMEOUT = 180.0


# --------------------------------------------------------------------------- #
# Shared pipeline (plan §4.1)
# --------------------------------------------------------------------------- #
class BaseBackend:
    """Preprocess + prompt + staged parse fallback (§7.5/§7.7)."""

    def __init__(self, provider: ProviderConfig) -> None:
        self.provider = provider
        self.backend_id = provider.id

    def _complete(
        self, image_bytes: bytes, mime: str, prompt: str, *, structured: bool = True
    ) -> str:
        raise NotImplementedError

    def analyze(
        self,
        image_path: Path,
        prompt: str,
        *,
        schema: bool = True,
    ) -> VisionReportBody:
        if not image_path.exists():
            raise VisionError(
                VisionErrorCode.BAD_REQUEST, f"Image file does not exist: {image_path}"
            )
        cfg = load_config()
        image_bytes, mime, _w, _h = preprocess(
            image_path, max_long_edge=cfg.max_long_edge, downscale=cfg.downscale
        )

        full_prompt = prompt + (report_mod.SCHEMA_INSTRUCTION if schema else "")
        raw = self._complete(image_bytes, mime, full_prompt, structured=schema)

        parsed = report_mod.try_parse(raw)
        if parsed is not None:
            return parsed
        if not schema:
            # Free-form prompts: no schema, no corrective retry (plan §5.6).
            return report_mod.degraded(raw)

        # One corrective retry (plan §7.7 step 3).
        corrective = report_mod.CORRECTIVE_INSTRUCTION + raw + report_mod.SCHEMA_INSTRUCTION
        try:
            raw2 = self._complete(image_bytes, mime, corrective, structured=True)
        except VisionError:
            return report_mod.degraded(raw)
        parsed2 = report_mod.try_parse(raw2)
        if parsed2 is not None:
            return parsed2

        # Lossless fallback (plan §7.7 step 4).
        return report_mod.degraded(raw2 or raw)


# --------------------------------------------------------------------------- #
# Error mapping (plan §4.2)
# --------------------------------------------------------------------------- #
def map_status(status: int, exc: Exception | None = None) -> VisionError:
    msg = str(exc) if exc else f"HTTP {status}"
    retry_after = None
    if exc is not None and isinstance(exc, httpx.HTTPStatusError):
        ra = exc.response.headers.get("retry-after")
        if ra:
            try:
                retry_after = float(ra)
            except ValueError:
                retry_after = None
    code = {
        400: VisionErrorCode.BAD_REQUEST,
        401: VisionErrorCode.AUTH_FAILED,
        402: VisionErrorCode.QUOTA_EXCEEDED,
        403: VisionErrorCode.AUTH_FAILED,
        404: VisionErrorCode.MODEL_NOT_FOUND,
        413: VisionErrorCode.BAD_REQUEST,
        415: VisionErrorCode.BAD_REQUEST,
        422: VisionErrorCode.BAD_REQUEST,
        429: VisionErrorCode.RATE_LIMIT,
    }.get(status)
    if code is None:
        code = VisionErrorCode.SERVER_ERROR if status >= 500 else VisionErrorCode.UNKNOWN
    return VisionError(code, msg, http_status=status, retry_after_sec=retry_after)


def map_httpx_error(exc: Exception) -> VisionError:
    """Translate an httpx exception into a VisionError (plan §7.8.1)."""
    if isinstance(exc, httpx.TimeoutException):
        return VisionError(VisionErrorCode.TIMEOUT, str(exc) or "request timed out")
    if isinstance(exc, httpx.HTTPStatusError):
        return map_status(exc.response.status_code, exc)
    if isinstance(exc, httpx.HTTPError):
        return VisionError(VisionErrorCode.NETWORK, str(exc) or "network error")
    return VisionError(VisionErrorCode.UNKNOWN, str(exc) or "unknown error")


def _json_object(resp: httpx.Response) -> dict:
    """Decode a provider response and enforce the object-shaped API contract."""
    try:
        data = resp.json()
    except (TypeError, ValueError) as exc:
        raise VisionError(
            VisionErrorCode.RESPONSE_INVALID, "Provider returned a non-JSON response."
        ) from exc
    if not isinstance(data, dict):
        raise VisionError(
            VisionErrorCode.RESPONSE_INVALID,
            f"Provider returned JSON {type(data).__name__}; expected an object.",
        )
    return data


# --------------------------------------------------------------------------- #
# OpenAI-compatible backend (opencode-go / opencode / openrouter / openai / custom)
# --------------------------------------------------------------------------- #
class OpenAICompatibleBackend(BaseBackend):
    def __init__(
        self, provider: ProviderConfig, api_key: str | None, *, base_url: str | None
    ) -> None:
        super().__init__(provider)
        self.api_key = api_key
        if not base_url:
            raise VisionError(
                VisionErrorCode.BAD_REQUEST,
                "A custom provider requires base_url.",
            )
        self.base_url = base_url.rstrip("/")
        self.model = provider.model or CATALOG[provider.type].default_model

    def _complete(
        self, image_bytes: bytes, mime: str, prompt: str, *, structured: bool = True
    ) -> str:
        if not self.model:
            raise VisionError(VisionErrorCode.MODEL_NOT_FOUND, "No model name specified.")
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_uri = f"data:{mime};base64,{b64}"
        body = {
            "model": self.model,
            "max_tokens": _MAX_TOKENS,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": BROWSER_UA,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            # Custom gateways may not require a key; other types must have one.
            if CATALOG[self.provider.type].key_required:
                raise VisionError(VisionErrorCode.AUTH_FAILED, "Missing API key.")
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
                timeout=_CLOUD_TIMEOUT,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise map_httpx_error(exc) from exc

        data = _json_object(resp)
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise VisionError(VisionErrorCode.RESPONSE_INVALID, "Received an empty response.")
        finish = choices[0].get("finish_reason")
        if finish == "content_filter":
            raise VisionError(VisionErrorCode.CONTENT_FILTERED, "Blocked by the safety filter.")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise VisionError(VisionErrorCode.RESPONSE_INVALID, "Invalid response message.")
        text = message.get("content") or ""
        if isinstance(text, list):  # some providers return content parts
            text = "".join(
                p.get("text", "") if isinstance(p.get("text", ""), str) else ""
                for p in text
                if isinstance(p, dict)
            )
        if not isinstance(text, str) or not text:
            raise VisionError(VisionErrorCode.RESPONSE_INVALID, "Received an empty response.")
        return text


# --------------------------------------------------------------------------- #
# Anthropic backend (Messages API)
# --------------------------------------------------------------------------- #
class AnthropicBackend(BaseBackend):
    _API_VERSION = "2023-06-01"

    def __init__(self, provider: ProviderConfig, api_key: str | None) -> None:
        super().__init__(provider)
        self.api_key = api_key
        self.model = provider.model or CATALOG["anthropic"].default_model
        self.api_url = (
            provider.base_url or CATALOG["anthropic"].default_base_url or ""
        ).rstrip("/")

    def _complete(
        self, image_bytes: bytes, mime: str, prompt: str, *, structured: bool = True
    ) -> str:
        if not self.api_key:
            raise VisionError(VisionErrorCode.AUTH_FAILED, "Missing Anthropic API key.")
        b64 = base64.b64encode(image_bytes).decode("ascii")
        body = {
            "model": self.model,
            "max_tokens": _MAX_TOKENS,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime, "data": b64},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self._API_VERSION,
            "content-type": "application/json",
            "User-Agent": BROWSER_UA,
        }
        try:
            resp = httpx.post(self.api_url, json=body, headers=headers, timeout=_CLOUD_TIMEOUT)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise map_httpx_error(exc) from exc

        data = _json_object(resp)
        if data.get("stop_reason") == "refusal":
            raise VisionError(VisionErrorCode.CONTENT_FILTERED, "The model refused to respond.")
        parts = data.get("content")
        if not isinstance(parts, list):
            raise VisionError(VisionErrorCode.RESPONSE_INVALID, "Invalid Anthropic content.")
        text = "".join(
            p.get("text", "") if isinstance(p.get("text", ""), str) else ""
            for p in parts
            if isinstance(p, dict) and p.get("type") == "text"
        )
        if not text:
            raise VisionError(VisionErrorCode.RESPONSE_INVALID, "Received an empty response.")
        return text


# --------------------------------------------------------------------------- #
# Ollama backend (local /api/chat)
# --------------------------------------------------------------------------- #
class OllamaBackend(BaseBackend):
    def __init__(self, provider: ProviderConfig, *, host: str) -> None:
        super().__init__(provider)
        self.host = host.rstrip("/")
        self.model = provider.model or CATALOG["ollama"].default_model

    def _complete(
        self, image_bytes: bytes, mime: str, prompt: str, *, structured: bool = True
    ) -> str:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        body = {
            "model": self.model,
            "stream": False,
            # Reasoning models (e.g. qwen3-vl) default to thinking ON, which sends
            # the whole answer to message.thinking and leaves message.content empty
            # (or just "{}"). Turn it off so the answer lands in content.
            "think": False,
            "messages": [{"role": "user", "content": prompt, "images": [b64]}],
        }
        if structured:
            body["format"] = "json"
        data = self._chat(body)
        message = data.get("message")
        if not isinstance(message, dict):
            raise VisionError(VisionErrorCode.RESPONSE_INVALID, "Invalid Ollama response.")
        text = message.get("content") or ""
        if not isinstance(text, str):
            raise VisionError(VisionErrorCode.RESPONSE_INVALID, "Invalid Ollama content.")
        if not text.strip():
            # Safety net: a reasoning model may still have put text in `thinking`.
            thinking = message.get("thinking") or ""
            if not isinstance(thinking, str):
                raise VisionError(VisionErrorCode.RESPONSE_INVALID, "Invalid Ollama thinking.")
            text = thinking.strip()
        if not text.strip():
            raise VisionError(VisionErrorCode.RESPONSE_INVALID, "Received an empty response.")
        return text

    def _chat(self, body: dict) -> dict:
        headers = {"User-Agent": BROWSER_UA}
        try:
            resp = httpx.post(f"{self.host}/api/chat", json=body, headers=headers,
                              timeout=_OLLAMA_TIMEOUT)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise VisionError(
                VisionErrorCode.OLLAMA_UNAVAILABLE,
                f"Cannot connect to the local Ollama server ({self.host}).",
            ) from exc
        except httpx.HTTPStatusError as exc:
            # Non-reasoning models / older Ollama may reject the `think` field with
            # a 400. Retry once without it (text-independent) so plain VLMs like
            # llava still work.
            if "think" in body and exc.response.status_code == 400:
                return self._chat({k: v for k, v in body.items() if k != "think"})
            if exc.response.status_code == 404:
                raise VisionError(
                    VisionErrorCode.OLLAMA_UNAVAILABLE,
                    f"Model '{self.model}' not found. Run 'ollama pull {self.model}' and retry.",
                    http_status=404,
                ) from exc
            raise map_httpx_error(exc) from exc
        except httpx.HTTPError as exc:
            raise map_httpx_error(exc) from exc

        return _json_object(resp)


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #
def build_backend(provider: ProviderConfig, api_key: str | None) -> BaseBackend:
    spec = CATALOG[provider.type]
    if spec.interface == "anthropic":
        return AnthropicBackend(provider, api_key)
    if spec.interface == "ollama":
        return OllamaBackend(
            provider, host=provider.base_url or spec.default_base_url or ""
        )
    return OpenAICompatibleBackend(
        provider, api_key, base_url=provider.base_url or spec.default_base_url
    )
