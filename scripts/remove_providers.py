"""Remove every registered provider (and its keychain key).

Usage: python remove_providers.py [path-to-orca-vision-helper-cli]

Runs `provider list`, then removes each provider. Failures are reported but
do not stop the remaining removals. Used by the uninstall scripts.
"""

from __future__ import annotations

import json
import subprocess
import sys

CLI = sys.argv[1] if len(sys.argv) > 1 else ".venv/bin/orca-vision-helper"


def main() -> int:
    out = subprocess.run(
        [CLI, "provider", "list"], capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        print(f"'provider list' failed: {out.stderr.strip()}", file=sys.stderr)
        return 1
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        print("'provider list' output was not JSON — nothing to remove.", file=sys.stderr)
        return 0
    removed = 0
    for p in data.get("providers", []):
        result = subprocess.run(
            [CLI, "provider", "remove", p["id"]],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print(f"removed provider: {p['id']}")
            removed += 1
        else:
            print(
                f"failed to remove provider {p['id']}: {result.stderr.strip()}",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
