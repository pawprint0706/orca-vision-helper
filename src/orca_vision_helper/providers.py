"""Provider catalog (plan §3 table, verbatim).

Each entry maps a `--type` to its interface, default base_url, default model,
and key source. `interface` selects the wire format: "openai" (OpenAI-compatible
chat/completions), "anthropic" (Messages API), "ollama" (/api/chat).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSpec:
    type: str
    name: str
    interface: str                 # "openai" | "anthropic" | "ollama"
    default_base_url: str | None
    default_model: str
    key_required: bool             # False for local/keyless providers
    env_var: str | None            # conventional env var fallback (None = none)


CATALOG: dict[str, ProviderSpec] = {
    spec.type: spec
    for spec in (
        ProviderSpec(
            type="opencode-go",
            name="OpenCode Go",
            interface="openai",
            default_base_url="https://opencode.ai/zen/go/v1",
            default_model="qwen3.6-plus",
            key_required=True,
            env_var="OPENCODE_API_KEY",
        ),
        ProviderSpec(
            type="opencode",
            name="OpenCode Zen",
            interface="openai",
            default_base_url="https://opencode.ai/zen/v1",
            default_model="claude-sonnet-4-6",
            key_required=True,
            env_var="OPENCODE_API_KEY",
        ),
        ProviderSpec(
            type="openrouter",
            name="OpenRouter",
            interface="openai",
            default_base_url="https://openrouter.ai/api/v1",
            default_model="anthropic/claude-sonnet-4.6",
            key_required=True,
            env_var="OPENROUTER_API_KEY",
        ),
        ProviderSpec(
            type="anthropic",
            name="Anthropic Claude",
            interface="anthropic",
            default_base_url="https://api.anthropic.com/v1/messages",
            default_model="claude-sonnet-4-6",
            key_required=True,
            env_var="ANTHROPIC_API_KEY",
        ),
        ProviderSpec(
            type="openai",
            name="OpenAI GPT",
            interface="openai",
            default_base_url="https://api.openai.com/v1",
            default_model="gpt-5.4",
            key_required=True,
            env_var="OPENAI_API_KEY",
        ),
        ProviderSpec(
            type="ollama",
            name="Ollama (local)",
            interface="ollama",
            default_base_url="http://localhost:11434",
            default_model="llava:7b",
            key_required=False,
            env_var=None,
        ),
        ProviderSpec(
            type="custom",
            name="Custom (OpenAI-compatible)",
            interface="openai",
            default_base_url=None,  # required
            default_model="",       # required
            key_required=False,     # key optional (gateways differ)
            env_var=None,
        ),
    )
}
