"""`orca-vision-helper` entry point — analyze images with a vision model (plan §5).

Subcommands:
  (none)           setup guide if unconfigured, else usage
  setup            interactive first-time setup (provider -> key -> model -> default)
  provider add     register a provider
  provider list    list registered providers (with key presence)
  provider update  change model / key / base_url
  provider remove  remove a provider (also deletes its keychain key)
  analyze <image>  analyze an image with the default/named provider
  check            settings / keys / endpoint probe
  models           supported providers + vision model list
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from . import auth
from . import config as cfg
from . import providers as prov
from .api import BROWSER_UA, DEFAULT_PROMPT, build_backend
from .errors import VisionError
from .models import ProviderConfig, VisionResult


def _resolve_key_arg(value: str | None) -> str | None:
    """If --key is '-', read it hidden via getpass so it never hits argv/logs."""
    if value == "-":
        return getpass.getpass("API key (hidden): ").strip() or None
    return value


def _prompt(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{question}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        return default or ""
    return value or default


def _print_json(obj: dict, *, ok: bool = True) -> int:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# setup
# --------------------------------------------------------------------------- #
def _cmd_setup(args) -> int:
    types = list(prov.CATALOG)
    print("Select a provider:")
    for i, t in enumerate(types, 1):
        spec = prov.CATALOG[t]
        print(f"  {i}. {spec.name} ({t}) — {spec.interface} — model: {spec.default_model or '(required)'}")
    choice = _prompt("Provider number")
    if not choice.isdigit() or not (1 <= int(choice) <= len(types)):
        print(f"invalid choice: {choice}", file=sys.stderr)
        return 1
    t = types[int(choice) - 1]
    spec = prov.CATALOG[t]

    if t == "custom":
        base_url = _prompt("Base URL (required)")
        if not base_url:
            print("custom provider requires --base-url / a base URL", file=sys.stderr)
            return 1
        model = _prompt("Model (required)")
        if not model:
            print("custom provider requires a model", file=sys.stderr)
            return 1
    else:
        base_url = spec.default_base_url
        model = _prompt("Model", spec.default_model)

    key_value = None
    if spec.key_required:
        key_value = getpass.getpass(
            "API key (empty = env var / opencode auth.json): "
        ).strip() or None

    key_ref = None
    if key_value:
        key_ref = auth.keyref_for(t)
        auth.set_key(key_ref, key_value)

    def mutate(latest: cfg.AppConfig) -> None:
        existing = latest.get_provider(t)
        if existing is not None:
            existing.model = model
            existing.base_url = base_url
            if key_value is not None:
                existing.key_ref = key_ref
        else:
            latest.add_provider(
                ProviderConfig(id=t, type=t, label=spec.name, model=model,
                               base_url=base_url, key_ref=key_ref)
            )
        # setup has no --set-default flag: a fresh default becomes the default,
        # an existing one is only replaced when it is the first provider.
        if getattr(args, "set_default", False) or latest.default_provider_id is None:
            latest.set_default_provider(t)

    config = cfg.update_config(mutate)
    return _print_json(
        {"status": "ok", "provider": t, "model": model, "default": config.default_provider_id}
    )


# --------------------------------------------------------------------------- #
# provider add / update / remove / list
# --------------------------------------------------------------------------- #
def _cmd_provider_help(parser):
    """`provider` without a subcommand prints its help instead of erroring."""

    def _run(_args) -> int:
        parser.print_help()
        return 0

    return _run


def _cmd_provider_add(args) -> int:
    config = cfg.load_config()
    pid = args.id or args.type
    if config.get_provider(pid):
        print(f"provider id already exists: {pid}", file=sys.stderr)
        return 1
    spec = prov.CATALOG[args.type]

    base_url = args.base_url or spec.default_base_url
    if args.type == "custom" and not base_url:
        print("custom provider requires --base-url", file=sys.stderr)
        return 1
    model = args.model or spec.default_model
    if args.type == "custom" and not model:
        print("custom provider requires --model", file=sys.stderr)
        return 1

    key_ref = None
    key_value = _resolve_key_arg(args.key)
    if key_value:
        key_ref = auth.keyref_for(pid)
        auth.set_key(key_ref, key_value)
    elif spec.key_required and not auth.resolve_key(
        ProviderConfig(id=pid, type=args.type)
    ):
        print(
            f"Warning: no key for '{args.type}'. Register with --key or set the env var "
            f"({spec.env_var or 'OPENCODE_API_KEY'}).",
            file=sys.stderr,
        )

    provider = ProviderConfig(
        id=pid,
        type=args.type,
        label=args.label or spec.name,
        model=model,
        base_url=base_url,
        key_ref=key_ref,
    )

    def add_provider(latest: cfg.AppConfig) -> None:
        latest.add_provider(provider)
        if args.set_default:
            latest.set_default_provider(pid)

    try:
        config = cfg.update_config(add_provider)
    except ValueError:
        if key_ref:
            auth.delete_key(key_ref)
        print(f"provider id already exists: {pid}", file=sys.stderr)
        return 1
    return _print_json(
        {"status": "ok", "added": pid, "default": config.default_provider_id}
    )


def _cmd_provider_update(args) -> int:
    config = cfg.load_config()
    provider = config.get_provider(args.id)
    if provider is None:
        print(f"provider not found: {args.id}", file=sys.stderr)
        return 1
    key_value = _resolve_key_arg(args.key)
    if key_value is not None:
        provider.key_ref = provider.key_ref or auth.keyref_for(provider.id)
        auth.set_key(provider.key_ref, key_value)
    key_ref = provider.key_ref

    def update_provider(latest: cfg.AppConfig) -> None:
        current = latest.get_provider(args.id)
        if current is None:
            return
        if args.type is not None:
            current.type = args.type
        if args.model is not None:
            current.model = args.model
        if args.label is not None:
            current.label = args.label
        if args.base_url is not None:
            current.base_url = args.base_url
        if key_value is not None:
            current.key_ref = key_ref
        if args.set_default:
            latest.set_default_provider(current.id)

    config = cfg.update_config(update_provider)
    provider = config.get_provider(args.id)
    if provider is None:
        print(f"provider not found: {args.id}", file=sys.stderr)
        return 1
    return _print_json(
        {"status": "ok", "updated": provider.id, "type": provider.type,
         "model": provider.model, "base_url": provider.base_url}
    )


def _cmd_provider_remove(args) -> int:
    config = cfg.load_config()
    provider = config.get_provider(args.id)
    if provider is None:
        print(f"provider not found: {args.id}", file=sys.stderr)
        return 1
    if provider.key_ref:
        auth.delete_key(provider.key_ref)
    config = cfg.update_config(lambda latest: latest.remove_provider(args.id))
    return _print_json(
        {"status": "ok", "removed": args.id, "default": config.default_provider_id}
    )


def _cmd_provider_list(_args) -> int:
    config = cfg.load_config()
    out = {
        "default_provider_id": config.default_provider_id,
        "last_used_provider_id": config.last_used_provider_id,
        "providers": [
            {"id": p.id, "type": p.type, "model": p.model, "base_url": p.base_url,
             "has_key": auth.has_key(p)}
            for p in config.providers
        ],
    }
    return _print_json(out)


# --------------------------------------------------------------------------- #
# analyze
# --------------------------------------------------------------------------- #
def _format_report(report) -> str:
    if report.parse_degraded:
        return report.raw_text
    lines = [f"Summary: {report.summary}"]
    if report.issues:
        lines.append("Issues:")
        for it in report.issues:
            where = it.region or it.element or "-"
            hint = f" (css: {it.css_hint})" if it.css_hint else ""
            lines.append(f"- [{it.severity}] {where}: {it.description}{hint}")
    else:
        lines.append("Issues: none")
    return "\n".join(lines)


def _cmd_analyze(args) -> int:
    image = Path(args.image).expanduser()
    if not image.exists():
        return _print_json({
            "status": "error", "error_code": "BAD_REQUEST",
            "message": f"Image file does not exist: {image}",
        }, ok=False)

    config = cfg.load_config()
    provider = config.get_provider(args.provider) if args.provider else config.effective_default()
    if provider is None:
        return _print_json({
            "status": "error",
            "message": "No provider registered. Run 'orca-vision-helper setup' first.",
        }, ok=False)

    if args.model:
        provider = provider.model_copy(update={"model": args.model})

    api_key = auth.resolve_key(provider)
    if not provider.is_local and api_key is None:
        return _print_json({
            "status": "error", "provider": provider.id,
            "error_code": "AUTH_FAILED",
            "message": f"No API key found for provider '{provider.id}'.",
            "next_action": f"Set {prov.CATALOG[provider.type].env_var or 'the provider key'} "
                           "or run 'orca-vision-helper provider update <id> --key -'.",
        }, ok=False)

    try:
        backend = build_backend(provider, api_key)
    except VisionError as exc:
        return _print_json(exc.to_result(provider.id), ok=False)

    prompt = args.prompt if args.prompt is not None else DEFAULT_PROMPT
    try:
        report = backend.analyze(image, prompt, schema=args.prompt is None)
    except VisionError as exc:
        return _print_json(exc.to_result(provider.id), ok=False)

    cfg.update_config(
        lambda latest: latest.mark_used(provider.id) if latest.get_provider(provider.id) else None
    )

    if args.json:
        return _print_json(VisionResult(provider=provider.id, report=report).model_dump())
    print(_format_report(report))
    return 0


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #
def _probe_endpoint(provider: ProviderConfig, api_key: str | None) -> dict:
    import httpx

    spec = prov.CATALOG[provider.type]
    base = (provider.base_url or spec.default_base_url or "").rstrip("/")
    if provider.is_local:
        url, ok_statuses = f"{base}/api/tags", (200,)
        note = "200 expected"
    else:
        url, ok_statuses = f"{base}/models", (200, 401, 403)
        note = "200/401/403 (403 = list hidden; expected for opencode endpoints)"
    headers = {"User-Agent": BROWSER_UA}
    if api_key and not provider.is_local:
        if provider.type == "anthropic":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"
    try:
        resp = httpx.get(url, headers=headers, timeout=10.0)
        return {"url": url, "http_status": resp.status_code,
                "ok": resp.status_code in ok_statuses, "note": note}
    except httpx.TimeoutException:
        return {"url": url, "ok": False, "error": "timeout"}
    except httpx.HTTPError as exc:
        return {"url": url, "ok": False, "error": type(exc).__name__}


def _cmd_check(_args) -> int:
    config = cfg.load_config()
    providers = [
        {"id": p.id, "type": p.type, "model": p.model, "base_url": p.base_url,
         "has_key": auth.has_key(p)}
        for p in config.providers
    ]
    result: dict = {
        "config_path": str(cfg.config_path()),
        "configured": bool(config.providers),
        "default_provider_id": config.default_provider_id,
        "providers": providers,
        "ok": False,
    }

    ok = bool(config.providers)
    for p in config.providers:
        if not auth.has_key(p):
            ok = False
            break

    default = config.effective_default()
    if default is not None:
        endpoint = _probe_endpoint(default, auth.resolve_key(default))
        result["endpoint"] = endpoint
        if endpoint["ok"] is False:
            ok = False
    result["ok"] = ok
    return _print_json(result, ok=ok)


# --------------------------------------------------------------------------- #
# models
# --------------------------------------------------------------------------- #
def _vision_models_from_cache() -> dict[str, list[str]]:
    """Vision-capable model ids from the opencode models.dev cache, if present."""
    path = Path.home() / ".cache/opencode/models.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, list[str]] = {}
    for t in ("opencode-go", "opencode"):
        entry = data.get(t)
        if not isinstance(entry, dict):
            continue
        models = entry.get("models") or {}
        vids = sorted(
            mid
            for mid, it in models.items()
            if isinstance(it, dict)
            and "image" in ((it.get("modalities") or {}).get("input") or [])
        )
        if vids:
            out[t] = vids
    return out


def _cmd_models(_args) -> int:
    out: dict = {
        "providers": [
            {"type": s.type, "name": s.name, "interface": s.interface,
             "default_model": s.default_model, "base_url": s.default_base_url,
             "key_required": s.key_required, "env_var": s.env_var}
            for s in prov.CATALOG.values()
        ]
    }
    cache = _vision_models_from_cache()
    if cache:
        out["vision_models_cache"] = cache
    return _print_json(out)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="orca-vision-helper",
        description="Analyze images with a vision-capable model and return a text report.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="interactive first-time setup").set_defaults(func=_cmd_setup)

    p_prov = sub.add_parser("provider", help="manage vision providers")
    p_prov.set_defaults(func=_cmd_provider_help(p_prov))
    prov_sub = p_prov.add_subparsers(dest="prov_command")
    p_add = prov_sub.add_parser("add", help="register a provider")
    p_add.add_argument("--type", required=True, choices=list(prov.CATALOG))
    p_add.add_argument("--id", help="provider id (default = type)")
    p_add.add_argument("--label")
    p_add.add_argument("--model", help="model name (defaults to the catalog default)")
    p_add.add_argument("--base-url", dest="base_url",
                       help="endpoint override (required for custom)")
    p_add.add_argument("--key", help="API key ('-' = hidden prompt; omitted = env var / auth.json)")
    p_add.add_argument("--set-default", action="store_true")
    p_add.set_defaults(func=_cmd_provider_add)

    p_upd = prov_sub.add_parser("update", help="update a provider")
    p_upd.add_argument("id")
    p_upd.add_argument("--type", choices=list(prov.CATALOG))
    p_upd.add_argument("--model")
    p_upd.add_argument("--label")
    p_upd.add_argument("--base-url", dest="base_url")
    p_upd.add_argument("--key", help="replace the API key ('-' = hidden prompt; stored in the keychain)")
    p_upd.add_argument("--set-default", action="store_true")
    p_upd.set_defaults(func=_cmd_provider_update)

    p_rm = prov_sub.add_parser("remove", help="remove a provider (also deletes its keychain key)")
    p_rm.add_argument("id")
    p_rm.set_defaults(func=_cmd_provider_remove)

    prov_sub.add_parser("list", help="list registered providers").set_defaults(
        func=_cmd_provider_list
    )

    p_an = sub.add_parser("analyze", help="analyze an image file")
    p_an.add_argument("image")
    p_an.add_argument("--prompt", default=None,
                      help="custom analysis prompt (skips the default JSON schema)")
    p_an.add_argument("--provider", help="provider id (defaults to the effective default)")
    p_an.add_argument("--model", help="model override for this call")
    p_an.add_argument("--json", action="store_true", help="print the structured report")
    p_an.set_defaults(func=_cmd_analyze)

    sub.add_parser("check", help="check settings, keys, and the endpoint").set_defaults(
        func=_cmd_check
    )
    sub.add_parser("models", help="list supported providers and vision models").set_defaults(
        func=_cmd_models
    )

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        if not cfg.load_config().providers:
            print(
                "No provider configured. Run 'orca-vision-helper setup' first.",
                file=sys.stderr,
            )
            return 1
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
