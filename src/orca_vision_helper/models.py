"""Shared data models (ported from VGMCP core/models.py, plan §5, §7).

Pydantic models so they serialize cleanly into CLI output and the config file.
Capture models are removed — orca-vision-helper is analysis-only.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Vision (plan §5.3, §7)
# --------------------------------------------------------------------------- #
Severity = Literal["high", "medium", "low"]


class VisionIssue(BaseModel):
    severity: Severity = "medium"
    region: str = ""
    element: str = ""
    description: str = ""
    css_hint: str = ""


class VisionReportBody(BaseModel):
    summary: str = ""
    issues: list[VisionIssue] = Field(default_factory=list)
    raw_text: str = ""
    # True when structured parsing failed and we fell back to raw_text (plan §7.7).
    parse_degraded: bool = False


class VisionResult(BaseModel):
    status: Literal["ok"] = "ok"
    provider: str
    report: VisionReportBody


# --------------------------------------------------------------------------- #
# Provider registry (plan §3, §7.3)
# --------------------------------------------------------------------------- #
ProviderType = Literal[
    "opencode-go", "opencode", "openrouter", "anthropic", "openai", "ollama", "custom"
]


class ProviderConfig(BaseModel):
    """One registered vision provider (plan §7.3).

    API keys are NOT stored here — only `key_ref`, an identifier into the OS
    credential store (plan §7.6).
    """

    id: str
    type: ProviderType
    label: str = ""
    model: str = ""
    base_url: str | None = None  # required for type=="custom"; defaulted for others
    key_ref: str | None = None   # keyring identifier; None for ollama

    @property
    def is_local(self) -> bool:
        return self.type == "ollama"
