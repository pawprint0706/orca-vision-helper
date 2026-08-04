# AGENTS.md

## Scope

These instructions apply to agents working on the `orca-vision-helper`
repository itself. They are not the global tool-discovery rule distributed to
other repositories or harnesses.

The short, stable rule intended for global agent instructions is
[`docs/AGENT_TOOL_RULE.md`](docs/AGENT_TOOL_RULE.md). Do not copy this root file
into a harness's global instructions.

## Project boundaries

- This project is an analysis-only CLI. It accepts an existing local image,
  sends it to a configured vision provider, and returns a text report.
- Screen capture, desktop control, and browser automation are outside the v1
  implementation boundary.
- Provider credentials must not be written to the project config or committed
  to the repository. Keep the existing environment-variable, OpenCode auth,
  and OS-keychain separation.
- Cloud analysis can transmit screenshots to an external service. Do not send
  sensitive images, configure providers, access credentials, or install,
  update, or remove this package unless the user has authorized the action.
- If visual inspection is needed while working on this repository and the
  current agent cannot inspect the image reliably, use the globally installed
  `orca-vision-helper` command if available. Do not bootstrap or configure it
  merely because the command is missing.

## Change guidance

- Keep provider-specific models, recovery commands, and setup details out of
  `docs/AGENT_TOOL_RULE.md`; those belong in the CLI help, README, and install
  documentation because they change more frequently.
- Preserve the `BEGIN orca-vision-helper` and `END orca-vision-helper` markers
  in the distributable rule. They allow a previously installed block to be
  replaced without overwriting unrelated global instructions.
- When the discovery or installation workflow changes, keep
  `docs/AGENT_TOOL_RULE.md`, `README.md`, `docs/AGENT_INSTALL.md`,
  `docs/AGENT_UNINSTALL.md`, and the platform install/uninstall scripts in sync.
- Keep agent-facing installation and removal commands valid on both
  macOS/Linux and Windows; do not present POSIX-only commands as universal.
- The supported runtime is Python 3.11+. Source code uses the `src/` layout;
  tests are under `tests/`.

## Verification

When changes are authorized and development dependencies are already
available, use the focused tests first, then the full checks as appropriate:

```bash
python -m pytest -q
ruff check src/ tests/
```

Do not install missing dependencies solely to run verification without user
approval. Report any verification that could not be performed.
