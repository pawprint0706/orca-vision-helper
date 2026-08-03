# AGENTS.md

## orca-vision-helper — how to "see" images without vision

You may not have vision. This project is a CLI that sends an image to a
vision-capable model and returns a **text report** you can read. Whenever a
task requires understanding an image, use this tool instead of trying to read
the file directly.

Works in any harness (opencode, codex, Claude Code, Cursor, …) because it's
just a bash command.

### When to use

- You need to understand a screenshot or captured screen (e.g. from
  computer-use / browser tools).
- You need UI state: dialog/button text, layout overlap, clipping, alignment.

### How to use

```bash
# check availability (global command, or venv-relative inside the repo)
command -v orca-vision-helper || .venv/bin/orca-vision-helper --help

# default: UI layout-bug diagnosis report (JSON-schema, Summary: + Issues:)
orca-vision-helper analyze <image.png>

# free-form question (no schema)
orca-vision-helper analyze <image.png> --prompt "List every button text in this dialog."

# structured output / explicit provider
orca-vision-helper analyze <image.png> --json
orca-vision-helper analyze <image.png> --provider opencode --model claude-sonnet-4-6
```

Read the returned text report and continue working. If parsing failed, raw
text comes back with `parse_degraded` — still usable.

### Key behaviors

- A successful `analyze` promotes that provider to the default; later calls
  just work.
- `opencode-go` / `opencode` providers need no key entry (auto-detected).
- If unconfigured or you're unsure which provider to use: **ask the user**,
  or run `orca-vision-helper setup` / `orca-vision-helper check`.

### Errors (JSON: `status: "error"`, `error_code`, `next_action`)

| `error_code` | Response |
|---|---|
| `AUTH_FAILED` | `provider update <id> --key -` |
| `TIMEOUT` / `RATE_LIMIT` / `SERVER_ERROR` | retry after a few seconds |
| `MODEL_NOT_FOUND` | `provider update <id> --model M`; list with `models` |
| `OLLAMA_UNAVAILABLE` | `ollama serve` + `ollama pull <model>` |

### Privacy

Cloud providers send the image to an external API. For sensitive screens, ask
the user whether to use the local Ollama provider.

### Install / setup (if the command is missing)

Follow `docs/AGENT_INSTALL.md` (install, register the global command, then ask
the user which provider to set as default).
