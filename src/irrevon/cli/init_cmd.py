"""``irrevon init`` — scaffold local runtime files + apply migrations,
non-destructively (dx-api §3.1): commented default config, single-service
compose with a real readiness healthcheck, a placeholders-only
``.env.example``, and — when the configured ledger database is already
reachable — the plain-SQL migrations (idempotent; ADR-0022). No git, no
containers started, no credentials generated, no network beyond the configured
localhost Postgres."""

from __future__ import annotations

import json
import os
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
dsn = "postgresql://irrevon_app@localhost:5432/irrevon"

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
      POSTGRES_USER: postgres
      POSTGRES_DB: irrevon
      # Disposable LOCAL development only. The port is loopback-only and this
      # trust-auth database must never be used as a production deployment.
      POSTGRES_HOST_AUTH_METHOD: trust
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
# .env.example — local bootstrap only; no credential is stored here.
# Source this file before the second `irrevon init`. The admin DSN is used
# only for migrations; normal runtime config uses the non-superuser
# irrevon_app role and `irrevon serve` swaps to irrevon_read.
IRREVON_MIGRATION_DSN=postgresql://postgres@localhost:5432/irrevon
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

        # Local generated Compose exposes a migration-only admin DSN through a
        # named environment value. Runtime operations continue to use the
        # non-superuser DSN in irrevon.toml.
        migration_dsn = os.environ.get("IRREVON_MIGRATION_DSN")
        if not migration_dsn:
            db_note = (
                "migrations not attempted — set IRREVON_MIGRATION_DSN explicitly "
                "to the intended migration target, then re-run `irrevon init`"
            )
        else:
            migrations_applied = apply_migrations(migration_dsn)
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
        print(
            "\nnext: cp .env.example .env && set -a && . ./.env && set +a "
            "&& docker compose up -d --wait && irrevon init && irrevon doctor"
        )
    return 0
