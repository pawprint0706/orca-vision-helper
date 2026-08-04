"""Configuration persistence + provider registry (plan §4.2.4, §7.3).

Stored at ~/.config/orca-vision-helper/config.json (XDG-style). Only provider
metadata and key references live here — never raw API keys (plan §7.6).

Writes are atomic (temp file + os.replace) and guarded by a file lock.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from .errors import VisionError, VisionErrorCode
from .models import ProviderConfig

_PROCESS_LOCK = threading.RLock()


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "orca-vision-helper"


class AppConfig(BaseModel):
    """Top-level persisted configuration."""

    target_folder: str | None = None  # v1 unused (reserved)

    providers: list[ProviderConfig] = Field(default_factory=list)
    default_provider_id: str | None = None   # plan §7.3: first-registered, then last-used
    last_used_provider_id: str | None = None

    # Image preprocessing (plan §7.5)
    max_long_edge: int = 1568
    downscale: str = "auto"  # "auto" | "off"

    # ---- provider registry helpers (plan §7.3) ----------------------------- #
    def get_provider(self, provider_id: str) -> ProviderConfig | None:
        return next((p for p in self.providers if p.id == provider_id), None)

    def add_provider(self, provider: ProviderConfig) -> None:
        if self.get_provider(provider.id):
            raise ValueError(f"provider id already exists: {provider.id}")
        self.providers.append(provider)
        # First registered provider becomes the default (plan §7.3 rule 2).
        if self.default_provider_id is None:
            self.default_provider_id = provider.id

    def remove_provider(self, provider_id: str) -> None:
        self.providers = [p for p in self.providers if p.id != provider_id]
        if self.default_provider_id == provider_id:
            self.default_provider_id = self.providers[0].id if self.providers else None
        if self.last_used_provider_id == provider_id:
            self.last_used_provider_id = None

    def mark_used(self, provider_id: str) -> None:
        """Last-used becomes the effective default going forward (plan §7.3 rule 3)."""
        self.last_used_provider_id = provider_id
        self.default_provider_id = provider_id

    def set_default_provider(self, provider_id: str) -> bool:
        """Explicitly choose the default backend.

        effective_default() prioritizes last_used_provider_id, so an explicit
        choice MUST also pin last_used — otherwise a previously-used backend
        keeps winning and the user's selection silently has no effect.
        """
        if self.get_provider(provider_id) is None:
            return False
        self.default_provider_id = provider_id
        self.last_used_provider_id = provider_id
        return True

    def effective_default(self) -> ProviderConfig | None:
        """Resolve the default provider: last-used wins, else stored default."""
        for pid in (self.last_used_provider_id, self.default_provider_id):
            if pid:
                p = self.get_provider(pid)
                if p:
                    return p
        return self.providers[0] if self.providers else None


# --------------------------------------------------------------------------- #
# Load / save (atomic + locked)
# --------------------------------------------------------------------------- #
def config_path() -> Path:
    return config_dir() / "config.json"


@contextmanager
def _file_lock(target: Path, *, required: bool = False):
    """Best-effort cross-process lock via a sibling .lock file.

    POSIX uses fcntl.flock; Windows uses msvcrt byte-range locking.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_file = target.with_suffix(target.suffix + ".lock")
    try:
        import fcntl
    except ImportError:
        fcntl = None  # type: ignore[assignment]

    if fcntl is not None:
        with open(lock_file, "a+b") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
        return

    try:
        import msvcrt
    except ImportError:
        if required:
            raise RuntimeError("No config file-lock implementation is available")
        yield
        return

    with open(lock_file, "a+b") as fh:
        if fh.tell() == 0:
            fh.write(b" ")  # msvcrt.locking needs a non-empty region to lock
            fh.flush()
        fh.seek(0)
        locked = False
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)  # blocks ~10s then raises
            locked = True
        except OSError:
            if required:
                raise
        try:
            yield
        finally:
            if locked:
                fh.seek(0)
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass


def _load_config(path: Path) -> AppConfig:
    if not path.exists():
        return AppConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppConfig.model_validate(data)
    except (json.JSONDecodeError, OSError, ValidationError) as exc:
        raise VisionError(
            VisionErrorCode.BAD_REQUEST,
            f"Configuration is invalid and was not modified: {path} ({exc})",
        ) from exc


def load_config() -> AppConfig:
    return _load_config(config_path())


def _write_config(path: Path, config: AppConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.model_dump_json(indent=2, exclude_none=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def save_config(config: AppConfig) -> None:
    """Replace the full config snapshot."""
    path = config_path()
    with _PROCESS_LOCK, _file_lock(path):
        _write_config(path, config)


def update_config(mutator: Callable[[AppConfig], None]) -> AppConfig:
    """Apply a focused mutation to the latest config under one mandatory lock."""
    path = config_path()
    with _PROCESS_LOCK, _file_lock(path, required=True):
        config = _load_config(path)
        mutator(config)
        _write_config(path, config)
    return config
