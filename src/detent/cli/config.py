"""CLI configuration — ``detent.toml``, local-first (dx-api §6).

Precedence: command-line flags > ``DETENT_*`` env vars > detent.toml >
built-in defaults. Unknown keys are a ``config_invalid`` error, not a warning —
silent typos in a reliability tool's config are how baselines get
misconfigured. NO SECRETS IN THE FILE, EVER: credentials are referenced by
environment-variable NAME only.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from detent.errors import ConfigInvalid

__all__ = ["Config", "load_config"]

_KNOWN_TOP = {"schema_version", "ledger", "adapters", "demo"}
_KNOWN_LEDGER = {"dsn", "password_env"}
_KNOWN_ADAPTER = {"kind", "capability_declaration", "credentials"}
_KNOWN_DEMO = {"seed"}

DEFAULT_DSN = "postgresql://detent@localhost:5432/detent"


@dataclass(frozen=True, slots=True)
class Config:
    path: Path | None
    dsn: str = DEFAULT_DSN
    password_env: str | None = None
    adapters: dict[str, dict[str, Any]] = field(default_factory=dict)
    demo_seed: int = 42

    def resolved_dsn(self) -> str:
        """DSN with the password injected from the named env var (values live
        only in the environment — 12factor)."""
        if self.password_env:
            password = os.environ.get(self.password_env)
            if password and "password=" not in self.dsn and "@" in self.dsn:
                scheme, _, rest = self.dsn.partition("://")
                userinfo, _, hostpart = rest.rpartition("@")
                if userinfo and ":" not in userinfo:
                    return f"{scheme}://{userinfo}:{password}@{hostpart}"
        return self.dsn


def _find_config(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise ConfigInvalid(f"config file not found: {explicit}")
        return path
    env = os.environ.get("DETENT_CONFIG")
    if env:
        path = Path(env)
        if not path.is_file():
            raise ConfigInvalid(f"DETENT_CONFIG points at a missing file: {env}")
        return path
    current = Path.cwd()
    for directory in (current, *current.parents):
        candidate = directory / "detent.toml"
        if candidate.is_file():
            return candidate
    return None


def load_config(explicit: str | None = None) -> Config:
    path = _find_config(explicit)
    if path is None:
        return Config(path=None)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as err:
        raise ConfigInvalid(f"{path}: {err}") from err

    unknown = set(raw) - _KNOWN_TOP
    if unknown:
        raise ConfigInvalid(f"{path}: unknown keys {sorted(unknown)}")
    ledger = raw.get("ledger", {})
    if set(ledger) - _KNOWN_LEDGER:
        raise ConfigInvalid(
            f"{path}: unknown [ledger] keys {sorted(set(ledger) - _KNOWN_LEDGER)}"
        )
    demo = raw.get("demo", {})
    if set(demo) - _KNOWN_DEMO:
        raise ConfigInvalid(
            f"{path}: unknown [demo] keys {sorted(set(demo) - _KNOWN_DEMO)}"
        )
    adapters: dict[str, dict[str, Any]] = {}
    for name, entry in raw.get("adapters", {}).items():
        if set(entry) - _KNOWN_ADAPTER:
            raise ConfigInvalid(
                f"{path}: unknown [adapters.{name}] keys "
                f"{sorted(set(entry) - _KNOWN_ADAPTER)}"
            )
        adapters[name] = dict(entry)
    return Config(
        path=path,
        dsn=str(ledger.get("dsn", DEFAULT_DSN)),
        password_env=ledger.get("password_env"),
        adapters=adapters,
        demo_seed=int(demo.get("seed", 42)),
    )
