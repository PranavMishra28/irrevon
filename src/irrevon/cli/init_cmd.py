"""``irrevon init`` — scaffold local runtime files + apply migrations,
non-destructively (dx-api §3.1): commented default config, single-service
compose with a real readiness healthcheck, a placeholders-only
``.env.example``, and — when the configured ledger database is already
reachable — the plain-SQL migrations (idempotent; ADR-0022). No git, no
containers started, no credentials generated, no network beyond the configured
localhost Postgres."""

from __future__ import annotations

import json
from pathlib import Path

from irrevon.cli.config import Config
from irrevon.errors import IrrevonError, StorageUnavailable

IRREVON_TOML = """\
# irrevon.toml — local configuration. NO SECRETS IN THIS FILE, EVER.
# Secrets are referenced by environment-variable NAME only.

schema_version = "1"

[ledger]
# DSN may embed user/host/db but NEVER a password; the password comes from the
# env var named below (set it in .env, which is gitignored).
dsn = "postgresql://irrevon@localhost:5432/irrevon"
password_env = "IRREVON_LEDGER_PASSWORD"

[adapters.refdest-c2]
kind = "refdest"
capability_declaration = "refdest-c2.capability.json"
# the reference destination is credential-free and network-free (in-process)

[demo]
seed = 42
"""

COMPOSE_YAML = """\
# Single service. Irrevon itself runs on the host; only the ledger is
# containerized. PostgreSQL 17, digest-pinned (RFC-002 §2.1).
services:
  ledger-db:
    # postgres:17-alpine (17.10), digest-pinned
    image: postgres@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193
    environment:
      POSTGRES_USER: irrevon
      POSTGRES_DB: irrevon
      POSTGRES_PASSWORD: ${IRREVON_LEDGER_PASSWORD:?set it in .env}
    ports:
      - "127.0.0.1:5432:5432" # loopback only — never exposed off-host
    volumes:
      - irrevon-ledger:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s
volumes:
  irrevon-ledger:
"""

ENV_EXAMPLE = """\
# .env.example — copy to .env (gitignored) and fill in LOCAL values only.
# A production-scope credential anywhere is a stop-and-rotate incident
# (master doc §9). Placeholders only in this file.
IRREVON_LEDGER_PASSWORD=change-me-locally
"""

FILES = {
    "irrevon.toml": IRREVON_TOML,
    "compose.yaml": COMPOSE_YAML,
    ".env.example": ENV_EXAMPLE,
}


def run_init(
    directory: Path, config: Config, *, force: bool, as_json: bool
) -> int:
    written: list[str] = []
    skipped: list[str] = []
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in FILES.items():
        target = directory / name
        if target.exists() and not force:
            skipped.append(name)
            continue
        target.write_text(content, encoding="utf-8")
        written.append(name)

    # Apply pending migrations when the ledger DB is already up (idempotent —
    # first run typically happens before `docker compose up`, so unreachable is
    # a normal, non-fatal state here; doctor reports it explicitly).
    migrations_applied: list[str] | None = None
    db_note = None
    try:
        from irrevon.ledger.db import apply_migrations

        migrations_applied = apply_migrations(config.resolved_dsn())
    except StorageUnavailable:  # DB not up yet — expected on first run
        db_note = (
            "ledger DB not reachable yet — start it (docker compose up -d --wait) "
            "and re-run `irrevon init` to apply migrations"
        )
    except IrrevonError:
        # Preserve any existing typed error and its stable envelope.
        raise
    except Exception as err:
        # SQL, migration-integrity, and programming failures are never a
        # successful first run. Keep the public result stable and sanitized;
        # exception chaining retains local debugger context without rendering
        # the possibly credential-bearing exception text in the CLI envelope.
        raise IrrevonError(
            "ledger migration failed; initialization did not complete"
        ) from err

    if as_json:
        print(
            json.dumps(
                {
                    "schema_version": "1",
                    "written": written,
                    "skipped": skipped,
                    "migrations_applied": migrations_applied,
                    "db_note": db_note,
                    "next": "irrevon doctor",
                }
            )
        )
    else:
        for name in written:
            print(f"wrote   {name}")
        for name in skipped:
            print(f"skipped {name} (exists; use --force to overwrite)")
        if migrations_applied is not None:
            print(
                f"migrations: applied {migrations_applied or 'none (all current)'}"
            )
        elif db_note:
            print(f"note: {db_note}")
        print("\nnext: cp .env.example .env && docker compose up -d --wait && irrevon doctor")
    return 0
