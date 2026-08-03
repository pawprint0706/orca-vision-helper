"""Error taxonomy (ported from VGMCP core/errors.py, plan §7.8).

`VisionError` is raised on runtime failures (config is fine, the call failed).
The CLI converts it into a structured error report with a next_action hint.
"""

from __future__ import annotations

from enum import Enum


class VisionErrorCode(str, Enum):
    """Vision runtime error codes (plan §7.8.1)."""

    AUTH_FAILED = "AUTH_FAILED"            # 401/403 — invalid/expired key
    RATE_LIMIT = "RATE_LIMIT"             # 429
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"     # 402 / billing exhausted
    TIMEOUT = "TIMEOUT"                   # client timeout
    NETWORK = "NETWORK"                   # connection/DNS/offline
    SERVER_ERROR = "SERVER_ERROR"        # provider 5xx
    BAD_REQUEST = "BAD_REQUEST"          # 400/413/415/422 — model/image issue
    CONTENT_FILTERED = "CONTENT_FILTERED"  # safety filter blocked
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"  # 404 / unknown model
    OLLAMA_UNAVAILABLE = "OLLAMA_UNAVAILABLE"  # local server down / model missing
    RESPONSE_INVALID = "RESPONSE_INVALID"  # got a response but unusable
    UNKNOWN = "UNKNOWN"                   # unclassified

    @property
    def retryable(self) -> bool:
        return self in _RETRYABLE


_RETRYABLE: frozenset[VisionErrorCode] = frozenset(
    {
        VisionErrorCode.RATE_LIMIT,
        VisionErrorCode.TIMEOUT,
        VisionErrorCode.NETWORK,
        VisionErrorCode.SERVER_ERROR,
        VisionErrorCode.OLLAMA_UNAVAILABLE,
        VisionErrorCode.RESPONSE_INVALID,
        VisionErrorCode.UNKNOWN,
    }
)


# Default human guidance per code (plan §7.8.1 "권장 next_action").
NEXT_ACTION: dict[VisionErrorCode, str] = {
    VisionErrorCode.AUTH_FAILED: (
        "Check/re-enter the API key: 'orca-vision-helper provider update <id> --key -', "
        "or set the provider's env var."
    ),
    VisionErrorCode.RATE_LIMIT: "Retry after retry_after_sec, or specify a different provider.",
    VisionErrorCode.QUOTA_EXCEEDED: "Check billing/plan, or switch to the local (Ollama) provider.",
    VisionErrorCode.TIMEOUT: "Retry; if it persists, downscale the image or use another provider.",
    VisionErrorCode.NETWORK: "Check the network and retry (local providers are unaffected).",
    VisionErrorCode.SERVER_ERROR: "Retry shortly, or specify a different provider.",
    VisionErrorCode.BAD_REQUEST: "Check the model name and image format/size (review preprocessing).",
    VisionErrorCode.CONTENT_FILTERED: "Adjust the prompt/image, or use another provider.",
    VisionErrorCode.MODEL_NOT_FOUND: "Fix the model name: 'orca-vision-helper provider update <id> --model M'.",
    VisionErrorCode.OLLAMA_UNAVAILABLE: "Start 'ollama serve' and 'ollama pull <model>', then retry.",
    VisionErrorCode.RESPONSE_INVALID: "Retry, or use another provider.",
    VisionErrorCode.UNKNOWN: "Retry; if it persists, report with logs attached.",
}


class VisionError(Exception):
    """A vision backend call failed at runtime (plan §7.8)."""

    def __init__(
        self,
        code: VisionErrorCode,
        message: str,
        *,
        http_status: int | None = None,
        retry_after_sec: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retry_after_sec = retry_after_sec

    def to_result(self, provider: str) -> dict:
        """Serialize to the structured error result (plan §7.8)."""
        return {
            "status": "error",
            "provider": provider,
            "error_code": self.code.value,
            "retryable": self.code.retryable,
            "retry_after_sec": self.retry_after_sec,
            "http_status": self.http_status,
            "message": self.message,
            "next_action": NEXT_ACTION[self.code],
        }
