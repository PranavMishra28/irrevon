"""CLI configuration — ``irrevon.toml``, local-first (dx-api §6).

Precedence: command-line flags > ``IRREVON_*`` env vars > irrevon.toml >
built-in defaults. Unknown keys are a ``config_invalid`` error, not a warning —
silent typos in a reliability tool's config are how baselines get
misconfigured. NO SECRETS IN THE FILE, EVER: credentials are referenced by
environment-variable NAME only.
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from psycopg import ProgrammingError
from psycopg.conninfo import make_conninfo

from irrevon.errors import ConfigInvalid

__all__ = ["Config", "load_config"]

_KNOWN_TOP = {"schema_version", "ledger", "adapters", "demo"}
_KNOWN_LEDGER = {"dsn", "password_env"}
_KNOWN_ADAPTER = {"kind", "capability_declaration", "credentials"}
_KNOWN_DEMO = {"seed"}

DEFAULT_DSN = "postgresql://irrevon_app@localhost:5432/irrevon"
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _environment_name(path: Path, field_name: str, value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _ENV_NAME.fullmatch(value) is None:
        raise ConfigInvalid(
            f"{path}: {field_name} must name a portable environment variable"
        )
    return value


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
        password = os.environ.get(self.password_env) if self.password_env else None
        try:
            # Let libpq's parser and escaper merge connection parameters. Raw
            # string interpolation here would let URI delimiters or
            # connection-option-looking password text change DSN semantics.
            if password:
                return make_conninfo(self.dsn, password=password)
            return make_conninfo(self.dsn)
        except ProgrammingError as err:
            # Neither the configured DSN nor the environment value belongs in
            # an error envelope: either may contain a credential.
            raise ConfigInvalid(
                "ledger.dsn is not valid PostgreSQL connection information"
            ) from err


def _find_config(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise ConfigInvalid(f"config file not found: {explicit}")
        return path
    env = os.environ.get("IRREVON_CONFIG")
    if env:
        path = Path(env)
        if not path.is_file():
            raise ConfigInvalid(f"IRREVON_CONFIG points at a missing file: {env}")
        return path
    current = Path.cwd()
    for directory in (current, *current.parents):
        candidate = directory / "irrevon.toml"
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
    if raw.get("schema_version") != "1":
        raise ConfigInvalid(f'{path}: schema_version must be the string "1"')
    ledger = raw.get("ledger", {})
    if not isinstance(ledger, dict):
        raise ConfigInvalid(f"{path}: ledger must be a table")
    if set(ledger) - _KNOWN_LEDGER:
        raise ConfigInvalid(
            f"{path}: unknown [ledger] keys {sorted(set(ledger) - _KNOWN_LEDGER)}"
        )
    demo = raw.get("demo", {})
    if not isinstance(demo, dict):
        raise ConfigInvalid(f"{path}: demo must be a table")
    if set(demo) - _KNOWN_DEMO:
        raise ConfigInvalid(
            f"{path}: unknown [demo] keys {sorted(set(demo) - _KNOWN_DEMO)}"
        )
    adapters: dict[str, dict[str, Any]] = {}
    raw_adapters = raw.get("adapters", {})
    if not isinstance(raw_adapters, dict):
        raise ConfigInvalid(f"{path}: adapters must be a table")
    for name, entry in raw_adapters.items():
        if not isinstance(entry, dict):
            raise ConfigInvalid(f"{path}: [adapters.{name}] must be a table")
        if set(entry) - _KNOWN_ADAPTER:
            raise ConfigInvalid(
                f"{path}: unknown [adapters.{name}] keys {sorted(set(entry) - _KNOWN_ADAPTER)}"
            )
        checked = dict(entry)
        checked["credentials"] = _environment_name(
            path, f"[adapters.{name}].credentials", entry.get("credentials")
        )
        if checked["credentials"] is None:
            checked.pop("credentials")
        for field_name in ("kind", "capability_declaration"):
            value = entry.get(field_name)
            if value is not None and (not isinstance(value, str) or not value):
                raise ConfigInvalid(
                    f"{path}: [adapters.{name}].{field_name} must be a non-empty string"
                )
        adapters[name] = checked
    dsn = ledger.get("dsn", DEFAULT_DSN)
    if not isinstance(dsn, str) or not dsn:
        raise ConfigInvalid(f"{path}: ledger.dsn must be a non-empty string")
    password_env = _environment_name(
        path, "ledger.password_env", ledger.get("password_env")
    )
    seed = demo.get("seed", 42)
    if type(seed) is not int or not 0 <= seed <= 2_147_483_647:
        raise ConfigInvalid(
            f"{path}: demo.seed must be an integer between 0 and 2147483647"
        )
    return Config(
        path=path,
        dsn=dsn,
        password_env=password_env,
        adapters=adapters,
        demo_seed=seed,
    )
