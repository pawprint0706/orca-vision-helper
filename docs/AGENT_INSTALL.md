# AGENT_INSTALL — Installation Instructions for AI Agents

> This document is written for **AI agents** (vision-blind coding models) that
> want to install, verify, and use orca-vision-helper on their own. Run every
> command with the bash tool. For human-readable docs, see [README.md](../README.md).

---

## 0. Check if already installed (skip §1–§2 if present)

```bash
which orca-vision-helper && orca-vision-helper --help >/dev/null 2>&1 && echo INSTALLED || echo NOT_INSTALLED
```

- If it prints `INSTALLED`, jump to **§3** (installation is a one-time task).
- If you suspect a stale version, just re-run `pip install -e .` to pick up the
  latest code.

## 1. Check prerequisites

```bash
python3 --version   # 3.11+ required (install 3.11+ if missing)
```

## 2. Install

From the project root (the directory containing `pyproject.toml`):

```bash
python3 -m venv .venv
.venv/bin/pip install -e . -q
```

- Calling `.venv/bin/…` directly (without activating the venv) is safe and does
  not affect the rest of your shell state.
- On success this creates the `orca-vision-helper` script.

## 3. Register a provider (one-time)

Register a vision model provider. opencode-go needs **no key entry** — the key
is auto-detected from `~/.local/share/opencode/auth.json` or `OPENCODE_API_KEY`:

```bash
.venv/bin/orca-vision-helper provider add --type opencode-go --set-default
.venv/bin/orca-vision-helper provider list   # confirm "has_key": true
```

- For other providers (anthropic/openrouter/openai etc.): run
  `provider add --type <t>`, then use the matching `*_API_KEY` env var or
  register a hidden key with `provider update <id> --key -`.
- For local Ollama: start `ollama serve`, then `provider add --type ollama`.

## 4. Analyze images (usage patterns)

```bash
# Default: UI layout-bug diagnosis report (overlap/alignment/clipping, JSON schema)
.venv/bin/orca-vision-helper analyze <image.png>

# Free-form question: no schema, answer in whatever format you want
.venv/bin/orca-vision-helper analyze <image.png> --prompt "List every button text in this dialog."

# Structured output
.venv/bin/orca-vision-helper analyze <image.png> --json

# Explicit provider/model (when not the default)
.venv/bin/orca-vision-helper analyze <image.png> --provider opencode --model claude-sonnet-4-6
```

### Interpreting the result

- Default output is a text report: `Summary:` + `Issues:`
  (severity/region/element/description/css_hint). **You (the main model) read
  this text and continue working.**
- If parsing failed, the raw text is returned as-is (`parse_degraded`).
- A successful `analyze` promotes that provider to the default (used
  automatically on the next call).

## 5. Handling errors

Errors are printed as JSON (`status: "error"`, `error_code`, `next_action`);
exit code is 0 (success) / 1 (failure).

| `error_code` | Response |
|---|---|
| `AUTH_FAILED` | Check the key: `provider update <id> --key -` or set the env var |
| `TIMEOUT` / `RATE_LIMIT` / `SERVER_ERROR` | Retry after a few seconds (retryable) |
| `MODEL_NOT_FOUND` | `provider update <id> --model M` — list models with `models` |
| `OLLAMA_UNAVAILABLE` | `ollama serve` + `ollama pull <model>` |
| `NETWORK` | Check connectivity, then retry |

- Decide whether to retry via the `retryable` field.
- If you see 403 / error 1010 (unexpected): User-Agent problem — make sure you
  run the latest version.

## 6. Other inspection commands

```bash
.venv/bin/orca-vision-helper check     # settings, keys, endpoint probe (ok: true/false)
.venv/bin/orca-vision-helper models    # supported providers + vision models
```

## Notes

- **External transmission consent**: with a cloud provider your screenshots are
  sent to an external API. For sensitive screens, use the local Ollama provider.
- Capturing is not this tool's job — analyze images that Orca's
  computer-use/browser-use already saved to files.
