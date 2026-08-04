# AGENT_INSTALL — Installation Instructions for AI Agents

> This document is for AI agents installing or configuring
> `orca-vision-helper` **after the user has explicitly approved those changes**.
> The absence of the command does not authorize package installation, `PATH`
> changes, provider registration, credential access, or edits to global agent
> instructions. Use the shell appropriate to the current environment. For
> human-readable docs, see [README.md](../README.md).

---

## 0. Check if already installed (skip §1–§2 if present)

Use the block for the current platform.

### macOS / Linux

```bash
if [ -x .venv/bin/orca-vision-helper ] && [ -f .venv/.cloud-upload-consent-v1 ]; then
    echo INSTALLED
elif [ -x .venv/bin/orca-vision-helper ]; then
    echo CONSENT_REQUIRED
else
    echo NOT_INSTALLED
fi
```

### Windows PowerShell

```powershell
$toolPath = ".venv\Scripts\orca-vision-helper.exe"
if ((Test-Path $toolPath) -and (Test-Path ".venv\.cloud-upload-consent-v1")) {
    "INSTALLED"
} elseif (Test-Path $toolPath) {
    "CONSENT_REQUIRED"
} else {
    "NOT_INSTALLED"
}
```

- Use the venv-relative check above. A global command lookup only succeeds when
  registration is already complete, so it is not an installation check.
- If it prints `CONSENT_REQUIRED`, complete §1.1 and record the marker command
  from §2 after affirmative consent. Reinstallation is not otherwise required.
- If it prints `INSTALLED`, verify the global command from §2 exists
  (`command -v orca-vision-helper` on macOS/Linux or
  `Get-Command orca-vision-helper` on Windows) and re-register it if missing.
  Global registration is a **required** install step. Then jump to **§3**.
- If you suspect a stale version, just re-run `pip install -e .` to pick up the
  latest code.

## 1. Check prerequisites

```bash
# macOS / Linux
python3 --version
```

```powershell
# Windows PowerShell
py -3 --version
```

Python 3.11 or newer is required. Installing Python itself also requires the
user's approval when it is missing.

## 1.1 Obtain cloud transmission consent

Before creating a virtual environment or installing anything, show the user
this material fact and obtain an explicit affirmative response:

> When a cloud or remote custom provider is configured, images selected for
> analysis are uploaded to that external service and may contain sensitive
> information. Local Ollama does not upload images.

Installation approval alone is not cloud transmission consent unless the user
was shown this notice. A blank, ambiguous, or negative response means stop; do
not install. The convenience scripts present this prompt themselves with a
default of No. Agents using the manual non-interactive flow must receive the
user's reply first and must not infer it from unrelated approval.

## 2. Install

From the project root (the directory containing `pyproject.toml`), use the
block for the current platform.

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/pip install -e . -q
printf '%s\n' cloud-upload-consent-v1 > .venv/.cloud-upload-consent-v1
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
& ".venv\Scripts\python.exe" -m pip install -e . -q
Set-Content ".venv\.cloud-upload-consent-v1" "cloud-upload-consent-v1" -NoNewline
```

- Calling the platform-specific executable directly without activating the venv
  is safe and does not affect the rest of the shell state.
- On success this creates the `orca-vision-helper` script.
- The marker records version 1 of the user's consent for this installation.
  Do not create it unless the explicit response required by §1.1 was received.
  A new consent version uses a new marker and requires a new response.

### Register the global command (required)

The venv-relative path only works from the repo root. The tool must be callable
from any directory, so register a global command. The install scripts do this
as a required step. Manual equivalents follow.

**macOS / Linux** — symlink into a bin dir on your PATH (e.g. `~/.local/bin`):

```bash
mkdir -p ~/.local/bin
ln -sfn "$(pwd)/.venv/bin/orca-vision-helper" ~/.local/bin/orca-vision-helper
```

- Confirm the bin dir is on your PATH:
  `echo "$PATH" | grep -q "$HOME/.local/bin"` — if not, add it
  (e.g. `export PATH="$HOME/.local/bin:$PATH"` in `~/.zshrc` / `~/.bashrc`).

**Windows PowerShell** — PATH shim instead (no admin rights needed):

```powershell
$shim = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\orca-vision-helper.cmd"
$exe = Join-Path (Get-Location) ".venv\Scripts\orca-vision-helper.exe"
Set-Content -LiteralPath $shim -Value "@echo off`r`n`"$exe`" %*" -Encoding ascii
```

- Verify with `Get-Command orca-vision-helper`. `$env:LOCALAPPDATA\Microsoft\WindowsApps`
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
| Codex | `$CODEX_HOME/AGENTS.md` (default: `~/.codex/AGENTS.md`) |
| Claude Code | `~/.claude/CLAUDE.md` |
| Cursor | **Cursor Settings → Rules → User Rules** |

For Codex, resolve the home directory first. If a non-empty
`AGENTS.override.md` already exists there, it is the active global instruction
file and must be updated instead of `AGENTS.md`:

```bash
codex_dir="${CODEX_HOME:-$HOME/.codex}"
```

In PowerShell, use
`$codexDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }`.

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

The file merge rules apply to OpenCode, Codex, and Claude Code. Cursor does not
document a user-level global rule file: open **Cursor Settings → Rules → User
Rules** and paste or replace the marked block there. User Rules are plain text;
project-local `.cursor/rules/*.mdc` files are not a substitute. Do not claim
that these editor User Rules also configure Cursor CLI.

The distributed rule intentionally contains only tool discovery, invocation,
and safety constraints. Provider details, model names, error recovery, and
installation instructions remain in the CLI help and repository docs so the
global context does not become stale or unnecessarily large.

Skipping this step is fine for interactive use when the human tells the agent
about the tool, but future sessions will not discover it on their own.

## 3. Choose and register the default provider (one-time)

**Ask the user which provider they want as the default — do not pick one
silently.** Run `orca-vision-helper models`, present its current provider and
default-model data, then ask for the provider and optional model override. This
command reads the same catalog used by the CLI and avoids stale model tables in
agent instructions. The selected default is used by every `analyze` call.

Interactive registration (recommended when a human is at the terminal — the
double-click install scripts do this automatically): the `setup` wizard walks
through provider selection, hidden key entry, and model choice, then sets the
default.

```text
orca-vision-helper setup
```

Scripted registration of the user's choice:

```text
orca-vision-helper provider add --type <chosen-type> [--model <chosen-model>] --set-default
orca-vision-helper provider list
orca-vision-helper check
```

- Omit `--model` to use the catalog default shown by `models`, unless the user
  chooses another compatible model. Custom providers require `--model` and
  `--base-url`.
- `has_key` reports literal credential presence. Require `has_key: true` only
  when `key_required: true`; Ollama and keyless custom providers can be usable
  with `has_key: false`. Use `check` to verify readiness.
- opencode-go/opencode need **no key entry** — the key is auto-detected from
  `~/.local/share/opencode/auth.json` or `OPENCODE_API_KEY`.
- For other providers (anthropic/openrouter/openai etc.): use the matching
  `*_API_KEY` env var or register a hidden key with `provider update <id> --key -`.
- For local Ollama: start `ollama serve` before registering
  (`provider add --type ollama`).

## 4. Analyze images (usage patterns)

```text
# Default: UI layout-bug diagnosis report (overlap/alignment/clipping, JSON schema)
orca-vision-helper analyze <image.png>

# Free-form question: no schema, answer in whatever format you want
orca-vision-helper analyze <image.png> --prompt "List every button text in this dialog."

# Structured output
orca-vision-helper analyze <image.png> --json

# Explicit provider/model (when not the default)
orca-vision-helper analyze <image.png> --provider <provider-id> --model <model-from-models-command>
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

```text
orca-vision-helper check     # model endpoint; HTTP 200 required
orca-vision-helper models    # supported providers + vision models
```

## Notes

- **External transmission consent** is collected during first installation as
  described in §1.1, not during the first analysis. With a cloud provider your
  screenshots are sent to an external API. For sensitive screens, use Ollama.
- Prefer hidden `--key -` input or an environment variable. A literal key passed
  on the command line can remain in shell history or a process list.
- Use HTTPS for remote custom providers. Plain HTTP is suitable only for a
  trusted local gateway.
- `check` reports connectivity, authentication validity, and model availability
  separately. `has_key` is literal credential presence; keyless custom and
  Ollama can be ready while reporting `has_key: false`.
- Capturing is not this tool's job — analyze images that Orca's
  computer-use/browser-use already saved to files.
