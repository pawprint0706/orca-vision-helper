# AGENT_UNINSTALL — Removal Instructions for AI Agents

> This document is written for **AI agents** (vision-blind coding models) that
> want to remove orca-vision-helper on their own. Run every command with the
> bash tool. For installation instructions, see [AGENT_INSTALL.md](AGENT_INSTALL.md).

---

## 0. Confirm it is installed (skip to §2 if already removed)

```bash
if [ -x .venv/bin/orca-vision-helper ]; then echo INSTALLED; else echo NOT_INSTALLED; fi
```

- Use the venv-relative check above — `which orca-vision-helper` only finds the
  tool when the venv is activated or it is on your PATH.
- If `NOT_INSTALLED`, still run §1 to clean up the config and keychain entries,
  if any.

## 1. Remove providers (recommended) — also deletes keychain keys

```bash
.venv/bin/orca-vision-helper provider list        # find registered provider ids
.venv/bin/orca-vision-helper provider remove <id> # one per registered provider
```

- This is the only clean way to delete the API keys stored in the OS keychain
  (keyring service `orca-vision-helper`).
- If the config was already deleted, `provider remove` can no longer find the
  providers — delete the keychain entries manually with your keyring manager
  (entries under service `orca-vision-helper`).

## 2. Delete the config directory

```bash
rm -rf ~/.config/orca-vision-helper
```

Removes `config.json` and its `.lock` file.

## 3. Uninstall the package

```bash
.venv/bin/pip uninstall orca-vision-helper -y
```

If the tool was installed into a different environment (e.g. system Python),
run the same command there — or just delete that venv.

## 4. (Optional) Remove the virtual environment

```bash
rm -rf .venv
```

## 5. Verify removal

```bash
which orca-vision-helper   # must print nothing
ls ~/.config/orca-vision-helper 2>/dev/null   # must print nothing
```

After §1–§5 there is no trace left in `~/.config`, the Python environment, or
the repository.
