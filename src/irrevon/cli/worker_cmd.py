"""``irrevon worker`` — CLI wiring for the continuous reconciliation service.

Adapters come from ``irrevon.toml`` ``[adapters.<id>]`` entries
(kind + optional capability_declaration path + credentials ENV-VAR NAME);
credential-gated kinds refuse to construct when the variable is unset
(config carries names, never values)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from irrevon.adapters.base import Adapter, declarations_dir, load_declaration
from irrevon.cli.config import Config
from irrevon.errors import ConfigInvalid

__all__ = ["build_adapters", "run_worker_cmd"]


def _declaration_for(entry: dict[str, Any], default_name: str) -> dict[str, Any]:
    if entry.get("capability_declaration"):
        return load_declaration(Path(str(entry["capability_declaration"])))
    return load_declaration(declarations_dir() / default_name)


def build_adapters(config: Config) -> dict[str, Adapter]:
    adapters: dict[str, Adapter] = {}
    for adapter_id, entry in sorted(config.adapters.items()):
        kind = str(entry.get("kind", ""))
        if kind == "refdest":
            from irrevon.adapters.refdest import RefdestAdapter

            base_url = os.environ.get("IRREVON_REFDEST_URL")
            if not base_url:
                raise ConfigInvalid(
                    f"[adapters.{adapter_id}] kind=refdest needs IRREVON_REFDEST_URL"
                )
            declaration = _declaration_for(entry, "refdest-c2.capability.json")
            adapters[adapter_id] = RefdestAdapter(
                adapter_id, declaration, base_url=base_url
            )
        elif kind == "stripe-c1":
            from irrevon.adapters.stripe_c1 import StripeC1Adapter

            adapters[adapter_id] = StripeC1Adapter.from_env(
                adapter_id,
                _declaration_for(entry, "stripe-c1.capability.json"),
                key_env=str(entry.get("credentials", "IRREVON_STRIPE_SANDBOX_KEY")),
            )
        elif kind == "easypost-c2":
            from irrevon.adapters.easypost_c2 import EasyPostC2Adapter

            adapters[adapter_id] = EasyPostC2Adapter.from_env(
                adapter_id,
                _declaration_for(entry, "easypost-c2.capability.json"),
                key_env=str(entry.get("credentials", "IRREVON_EASYPOST_TEST_KEY")),
            )
        else:
            raise ConfigInvalid(
                f"[adapters.{adapter_id}] unknown kind {kind!r} "
                "(known: refdest, stripe-c1, easypost-c2)"
            )
    if not adapters:
        raise ConfigInvalid(
            "the worker needs at least one [adapters.<id>] entry in irrevon.toml"
        )
    return adapters


def run_worker_cmd(
    config: Config,
    *,
    dsn: str | None,
    interval_s: float,
    sweep_interval_s: float,
    health_file: str | None,
    max_cycles: int | None,
) -> int:
    from irrevon.worker import WorkerConfig, run_worker

    adapters = build_adapters(config)
    print(
        f"worker: {len(adapters)} adapter(s) configured "
        f"({', '.join(sorted(adapters))}); reconcile every {interval_s:g}s, "
        f"sweep every {sweep_interval_s:g}s",
        file=sys.stderr,
    )
    return run_worker(
        dsn or config.resolved_dsn(),
        adapters,
        WorkerConfig(
            reconcile_interval_s=interval_s,
            sweep_interval_s=sweep_interval_s,
            health_file=Path(health_file) if health_file else None,
            max_cycles=max_cycles,
        ),
    )
