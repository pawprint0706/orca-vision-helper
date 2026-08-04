# AGENT_INSTALL — Installation Instructions for AI Agents

> This document is for AI agents installing or configuring
> `orca-vision-helper` **after the user has explicitly approved those changes**.
> The absence of the command does not authorize package installation, `PATH`
> changes, provider registration, credential access, or edits to global agent
> instructions. Use the shell appropriate to the current environment. For
> human-readable docs, see [README.md](../README.md).

---

## 0. Check if already installed (skip §1–§2 if present)

```bash
if [ -x .venv/bin/orca-vision-helper ] && .venv/bin/orca-vision-helper --help >/dev/null 2>&1; then
    echo INSTALLED
else
    echo NOT_INSTALLED
fi
```

- Use the venv-relative check above. `which orca-vision-helper` only succeeds
  when the venv is activated or the tool is on your PATH — a false
  `NOT_INSTALLED` is harmless: re-running the install in §2 is idempotent.
- If it prints `INSTALLED`, verify the global command from §2 exists
  (`command -v orca-vision-helper`) and re-register it if missing — global
  registration is a **required** install step, not an option. Then jump to **§3**.
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

### Register the global command (required)

The `.venv/bin/…` path only works while your working directory is the repo
root. The tool must be callable from any directory, so register a global
command — the double-click install scripts do this as a required step.
Manual equivalent:

**macOS / Linux** — symlink into a bin dir on your PATH (e.g. `~/.local/bin`):

```bash
mkdir -p ~/.local/bin
ln -sfn "$(pwd)/.venv/bin/orca-vision-helper" ~/.local/bin/orca-vision-helper
```

- Confirm the bin dir is on your PATH:
  `echo "$PATH" | grep -q "$HOME/.local/bin"` — if not, add it
  (e.g. `export PATH="$HOME/.local/bin:$PATH"` in `~/.zshrc` / `~/.bashrc`).

**Windows** — PATH shim instead (no admin rights needed):

```bat
(echo @echo off & echo "%CD%\.venv\Scripts\orca-vision-helper.exe" %%*) > "%LOCALAPPDATA%\Microsoft\WindowsApps\orca-vision-helper.cmd"
```

- Verify with `where orca-vision-helper`. `%LOCALAPPDATA%\Microsoft\WindowsApps`
  is on PATH by default on modern Windows; if not, add it to PATH manually.

Notes:

- The config (`~/.config/orca-vision-helper/`) and keys are global already —
  provider registration survives moving between directories.
- If the repo is moved, re-run the install script (or the `ln -s` / shim above)
  to refresh the global command.

### Register agent awareness (recommended)

A plain CLI is invisible to coding agents unless something puts it in their
context — there is no MCP-style tool list to discover it from. The stable,
short discovery rule intended for global instructions is
[`AGENT_TOOL_RULE.md`](AGENT_TOOL_RULE.md). The project-root `AGENTS.md` is for
agents developing this repository and must not be copied globally.

Global instruction registration is optional and changes user-level files.
Ask for explicit approval before editing them, even when package installation
was already approved. After approval, copy the complete block from
`AGENT_TOOL_RULE.md`, including its `BEGIN orca-vision-helper` and
`END orca-vision-helper` markers, to the relevant target:

| Harness | Global instructions file |
|---|---|
| opencode | `~/.config/opencode/AGENTS.md` |
| Codex | `~/.codex/AGENTS.md` |
| Claude Code | `~/.claude/CLAUDE.md` (newer versions also read `AGENTS.md`) |
| Cursor | a dedicated rule file such as `~/.cursor/rules/orca-vision-helper.md` |

Apply these merge rules:

1. Read the target first and preserve all unrelated instructions.
2. If neither marker exists, append one complete block with a separating blank
   line. Never overwrite the target file.
3. If both markers exist, replace only the text from the begin marker through
   the end marker. This updates an older rule without creating duplicates.
4. If only one marker exists, stop and ask the user how to resolve the malformed
   block rather than guessing its boundaries.
5. Read the result back and confirm that exactly one begin marker and one end
   marker remain.

The distributed rule intentionally contains only tool discovery, invocation,
and safety constraints. Provider details, model names, error recovery, and
installation instructions remain in the CLI help and repository docs so the
global context does not become stale or unnecessarily large.

Skipping this step is fine for interactive use when the human tells the agent
about the tool, but future sessions will not discover it on their own.

## 3. Choose and register the default provider (one-time)

**Ask the user which provider they want as the default — do not pick one
silently.** Show the supported providers (and their default models) from the
table below or `orca-vision-helper models`, ask for the provider and (if they
care) the model, then register their choice. The default provider is used by
every `analyze` call.

| type | provider | default model | key source |
|---|---|---|---|
| `opencode-go` | OpenCode Go | `qwen3.6-plus` | auto-detected (`auth.json` / `OPENCODE_API_KEY`) |
| `opencode` | OpenCode Zen | `claude-sonnet-4-6` | auto-detected (`auth.json` / `OPENCODE_API_KEY`) |
| `openrouter` | OpenRouter | `anthropic/claude-sonnet-4.6` | `OPENROUTER_API_KEY` / keychain |
| `anthropic` | Anthropic Claude | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` / keychain |
| `openai` | OpenAI GPT | `gpt-5.4` | `OPENAI_API_KEY` / keychain |
| `ollama` | Ollama (local) | `llava:7b` | none (local) |
| `custom` | Custom (OpenAI-compatible) | user-defined | keychain / keyless |

Interactive registration (recommended when a human is at the terminal — the
double-click install scripts do this automatically): the `setup` wizard walks
through provider selection, hidden key entry, and model choice, then sets the
default.

```bash
.venv/bin/orca-vision-helper setup
```

Scripted registration of the user's choice:

```bash
.venv/bin/orca-vision-helper provider add --type <chosen-type> --model <chosen-model> --set-default
.venv/bin/orca-vision-helper provider list   # confirm "has_key": true
```

- Model: use the provider's default above unless the user prefers another —
  list vision-capable models with `orca-vision-helper models`.
- opencode-go/opencode need **no key entry** — the key is auto-detected from
  `~/.local/share/opencode/auth.json` or `OPENCODE_API_KEY`.
- For other providers (anthropic/openrouter/openai etc.): use the matching
  `*_API_KEY` env var or register a hidden key with `provider update <id> --key -`.
- For local Ollama: start `ollama serve` before registering
  (`provider add --type ollama`).

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
