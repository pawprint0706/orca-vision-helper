# AGENT_INSTALL — Installation Instructions for AI Agents

> This document is written for **AI agents** (vision-blind coding models) that
> want to install, verify, and use orca-vision-helper on their own. Run every
> command with the bash tool. For human-readable docs, see [README.md](../README.md).

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
context — there is no MCP-style tool list to discover it from. To make every
agent session (in any harness: opencode / codex / Claude Code / Cursor …)
know about the tool, merge the project-root `AGENTS.md` into the global
instructions file(s) of the harnesses in use. These files are read
automatically at session start. **Always append** — never overwrite an
existing file with other instructions:

| Harness | Global instructions file |
|---|---|
| opencode | `~/.config/opencode/AGENTS.md` |
| Codex | `~/.codex/AGENTS.md` |
| Claude Code | `~/.claude/CLAUDE.md` (newer versions also read `AGENTS.md`) |
| Cursor | `~/.cursor/rules/` (global rules) |

Example (opencode; adapt the path per harness):

```bash
AGENTS_FILE="$HOME/.config/opencode/AGENTS.md"
mkdir -p "$(dirname "$AGENTS_FILE")" && touch "$AGENTS_FILE"
if ! grep -q "orca-vision-helper" "$AGENTS_FILE"; then
    { echo ""; cat AGENTS.md; } >> "$AGENTS_FILE"
    echo "Merged AGENTS.md into $AGENTS_FILE"
else
    echo "Already present in $AGENTS_FILE"
fi
```

- If a harness file already exists with other instructions, the append still
  works — instructions are additive; the `orca-vision-helper` section in
  `AGENTS.md` is already clearly headed, so it stays scoped.
- Skipping this step is fine for interactive use (the human tells the agent
  about the tool when needed), but agents will not discover it on their own.

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
