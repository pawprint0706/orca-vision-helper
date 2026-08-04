# AGENT_UNINSTALL — Removal Instructions for AI Agents

> This document is for AI agents removing `orca-vision-helper` **only after the
> user has explicitly approved removal**. Do not remove providers, credentials,
> configuration, the virtual environment, the global command, or agent
> instructions merely because the tool appears unused, missing, or broken. Use
> the shell and path syntax appropriate to the current operating system. For
> installation instructions, see [AGENT_INSTALL.md](AGENT_INSTALL.md).

The approval must cover the complete removal scope. If it covers only one item,
remove only that item and leave the rest intact.

## 0. Confirm the local installation

### macOS / Linux

```bash
if [ -x .venv/bin/orca-vision-helper ]; then echo INSTALLED; else echo NOT_INSTALLED; fi
```

### Windows PowerShell

```powershell
if (Test-Path ".venv\Scripts\orca-vision-helper.exe") { "INSTALLED" } else { "NOT_INSTALLED" }
```

If the local executable is absent, provider metadata or a global command may
still remain. Inspect each exact path below rather than assuming it is safe to
delete.

## 1. Remove providers and keychain credentials

Use the registered global command when it still works:

```text
orca-vision-helper provider list
orca-vision-helper provider remove <id>
```

Run `provider remove` once per registered provider. If the global command is
unavailable, use `.venv/bin/orca-vision-helper` on macOS/Linux or
`.venv\Scripts\orca-vision-helper.exe` on Windows.

This is the clean way to remove keys stored under the keyring service
`orca-vision-helper`. If configuration was already deleted, remove remaining
entries with the operating system's credential manager after confirming their
service and provider identifiers.

## 2. Delete configuration

### macOS / Linux

```bash
rm -rf -- "$HOME/.config/orca-vision-helper"
```

### Windows PowerShell

```powershell
$configPath = Join-Path $HOME ".config\orca-vision-helper"
Remove-Item -LiteralPath $configPath -Recurse -Force -ErrorAction SilentlyContinue
```

These exact paths contain `config.json` and its lock file.

## 3. Remove the registered global command

Do not delete a same-named command belonging to another installation. Inspect
the target or shim contents before removal.

### macOS / Linux

```bash
for command_path in /usr/local/bin/orca-vision-helper "$HOME/.local/bin/orca-vision-helper"; do
    if [ -L "$command_path" ]; then
        printf '%s -> %s\n' "$command_path" "$(readlink "$command_path")"
    fi
done
```

After confirming one printed symlink targets this repository's
`.venv/bin/orca-vision-helper`, remove only that explicit path:

```bash
rm -f -- <confirmed-symlink-path>
```

### Windows PowerShell

```powershell
$shimPath = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\orca-vision-helper.cmd"
if (Test-Path -LiteralPath $shimPath) {
    Get-Content -LiteralPath $shimPath
}
```

After confirming the displayed shim launches this repository's
`.venv\Scripts\orca-vision-helper.exe`, remove it:

```powershell
Remove-Item -LiteralPath $shimPath -Force
```

## 4. Uninstall the package and remove the consent record

### macOS / Linux

```bash
.venv/bin/python -m pip uninstall orca-vision-helper -y
rm -f -- .venv/.cloud-upload-consent-v1
```

### Windows PowerShell

```powershell
& ".venv\Scripts\python.exe" -m pip uninstall orca-vision-helper -y
Remove-Item -LiteralPath ".venv\.cloud-upload-consent-v1" -Force -ErrorAction SilentlyContinue
```

If the package was installed in another environment, use that environment's
Python. Removing the marker ensures a later fresh installation asks for the
current consent version again.

## 5. Remove the virtual environment

### macOS / Linux

```bash
rm -rf -- "$(pwd)/.venv"
```

### Windows PowerShell

```powershell
$venvPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) ".venv"))
Remove-Item -LiteralPath $venvPath -Recurse -Force
```

Before running either command, confirm the current directory is the repository
root and the resolved target is its `.venv` directory.

## 6. Remove the global agent-awareness rule

Remove exactly one block beginning with `<!-- BEGIN orca-vision-helper -->` and
ending with `<!-- END orca-vision-helper -->`. Preserve all unrelated content.
If only one marker exists, stop and ask the user rather than guessing a range.

- OpenCode: `~/.config/opencode/AGENTS.md`
- Codex: the active file under `CODEX_HOME` (default `~/.codex`): a non-empty
  `AGENTS.override.md` when present, otherwise `AGENTS.md`
- Claude Code: `~/.claude/CLAUDE.md`
- Cursor: open **Cursor Settings → Rules → User Rules** and remove only the
  marked block; `.cursor/rules` is project-local and is not the target

The project-root `AGENTS.md` is repository guidance and must not be removed as
part of global rule cleanup.

## 7. Verify removal

### macOS / Linux

```bash
command -v orca-vision-helper   # must print nothing
test ! -e "$HOME/.config/orca-vision-helper"
test ! -e "$(pwd)/.venv"
```

### Windows PowerShell

```powershell
Get-Command orca-vision-helper -ErrorAction SilentlyContinue  # no result expected
Test-Path (Join-Path $HOME ".config\orca-vision-helper")      # False expected
Test-Path ([System.IO.Path]::GetFullPath((Join-Path (Get-Location) ".venv"))) # False
```

Also verify that each approved global instruction target contains no
`BEGIN orca-vision-helper` marker. Only then is the approved removal complete.
