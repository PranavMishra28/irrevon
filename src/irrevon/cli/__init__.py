"""``irrevon`` CLI — the four first-slice commands (RFC-002 §12):
``init`` · ``doctor`` · ``demo`` · ``inspect``.

Conventions (dx-api §3.0): data on stdout, messages on stderr; ``--json`` /
``--jsonl`` with ``schema_version``; exit codes 0 success · 1 unexpected
failure · 2 usage · 3 declared outcome · 4 integrity refusal. Zero telemetry,
no update checks, no network beyond the configured adapters and localhost
Postgres (conformance-tested).

``serve`` (the loopback read-only workbench server) completes the product
journey ``install → init → doctor → demo → serve``.

``bench`` (fixtures/validate/smoke/analyze/run) landed with the benchmark
foundation (ADR-0030, proposed); ``bench run`` remains an integrity refusal
(exit 4) until the human Stage-B freeze exists. Deferred (RFC-002 §12):
operator verbs (M4).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from irrevon import __version__
from irrevon.errors import IrrevonError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="irrevon",
        description=(
            "Irrevon — reference reconciliation engine for irreversible "
            "AI-agent actions. Irrevon makes no network connections except to "
            "the destinations you configure and your own Postgres; there is no "
            "telemetry, no crash reporting, no update checking."
        ),
    )
    parser.add_argument("--version", action="version", version=f"irrevon {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", help="path to irrevon.toml", default=None)
    common.add_argument("-q", "--quiet", action="store_true")
    common.add_argument("--no-color", action="store_true")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser(
        "init",
        help="scaffold irrevon.toml, compose.yaml, .env.example",
        parents=[common],
    )
    p_init.add_argument("--force", action="store_true")
    p_init.add_argument("--dir", default=".")
    p_init.add_argument("--json", action="store_true")

    p_doctor = sub.add_parser(
        "doctor", help="read-only environment validation", parents=[common]
    )
    p_doctor.add_argument("--probe", action="store_true",
                          help="opt into declared read-only liveness calls")
    p_doctor.add_argument("--json", action="store_true")

    p_demo = sub.add_parser(
        "demo", help="the flagship demo incl. the B5 contrast leg", parents=[common]
    )
    p_demo.add_argument("--seed", type=int, default=None)
    p_demo.add_argument("--leg", choices=("irrevon", "b5", "both"), default="both")
    p_demo.add_argument("--keep", action=argparse.BooleanOptionalAction, default=True,
                        help="retain the demo database for `irrevon inspect`")
    p_demo.add_argument("--jsonl", action="store_true")
    p_demo.add_argument("--artifact", default="./irrevon-demo-artifact.json",
                        help="write the demo events + summary here on completion "
                             "(`irrevon serve` exposes it at /api/v1/demo/artifact)")
    p_demo.add_argument("--no-artifact", action="store_true",
                        help="skip writing the demo artifact file")

    p_serve = sub.add_parser(
        "serve",
        help="loopback read-only workbench server (127.0.0.1 only; GET/HEAD only)",
        parents=[common],
    )
    p_serve.add_argument(
        "--port", type=int, default=5180,
        help="port on 127.0.0.1 (default 5180; 0 binds an ephemeral port — "
             "read the real one from the ready line)",
    )
    p_serve.add_argument("--dsn", default=None,
                         help="override the ledger DSN (e.g. a kept demo database)")
    p_serve.add_argument("--demo-artifact", default="./irrevon-demo-artifact.json",
                         help="file backing /api/v1/demo/artifact")
    p_serve.add_argument("--open", action="store_true",
                         help="open the workbench in the default browser")
    p_serve.add_argument("--json", action="store_true",
                         help="print the ready line as one JSON document on stdout")

    from irrevon.cli.bench_cmd import add_bench_parser

    add_bench_parser(sub, common)

    p_worker = sub.add_parser(
        "worker",
        help="continuous reconciliation service (single-writer; ADR-0034 proposed)",
        parents=[common],
    )
    p_worker.add_argument("--dsn", default=None,
                          help="override the ledger DSN")
    p_worker.add_argument("--interval", type=float, default=30.0,
                          help="reconcile-cycle interval in seconds (default 30)")
    p_worker.add_argument("--sweep-interval", type=float, default=300.0,
                          help="orphan-sweep interval in seconds (default 300)")
    p_worker.add_argument("--health-file", default=None,
                          help="freshness file refreshed every cycle "
                               "(liveness-probe target for non-HTTP deployments)")
    p_worker.add_argument("--max-cycles", type=int, default=None,
                          help="stop after N cycles (operational/test affordance; "
                               "default: run until SIGTERM/SIGINT)")

    p_inspect = sub.add_parser(
        "inspect", help="the ledger-only evidence view", parents=[common]
    )
    p_inspect.add_argument("identifier")
    p_inspect.add_argument("--reveal", action="store_true",
                           help="show stable-id values (redacted by default)")
    p_inspect.add_argument("--json", action="store_true")
    p_inspect.add_argument("--dsn", default=None,
                           help="override the ledger DSN (e.g. a kept demo database)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    try:
        from irrevon.cli.config import load_config

        config = load_config(args.config)
        if args.command == "init":
            from irrevon.cli.init_cmd import run_init

            return run_init(
                Path(args.dir), config, force=args.force, as_json=args.json
            )
        if args.command == "doctor":
            from irrevon.cli.doctor import run_doctor

            return run_doctor(config, probe=args.probe, as_json=args.json)
        if args.command == "demo":
            from irrevon.cli.demo import run_demo

            seed = args.seed if args.seed is not None else config.demo_seed
            artifact = None if args.no_artifact else Path(args.artifact)
            return run_demo(
                config,
                seed=seed,
                leg=args.leg,
                keep=args.keep,
                jsonl=args.jsonl,
                artifact=artifact,
            )
        if args.command == "serve":
            import dataclasses

            from irrevon.serve import run_serve

            serve_config = (
                dataclasses.replace(config, dsn=args.dsn) if args.dsn else config
            )
            return run_serve(
                serve_config,
                port=args.port,
                demo_artifact=args.demo_artifact,
                open_browser=args.open,
                as_json=args.json,
                quiet=args.quiet,
            )
        if args.command == "bench":
            from irrevon.cli.bench_cmd import run_bench

            return run_bench(args, config)
        if args.command == "worker":
            from irrevon.cli.worker_cmd import run_worker_cmd

            return run_worker_cmd(
                config,
                dsn=args.dsn,
                interval_s=args.interval,
                sweep_interval_s=args.sweep_interval,
                health_file=args.health_file,
                max_cycles=args.max_cycles,
            )
        if args.command == "inspect":
            from irrevon.cli.inspect_cmd import run_inspect

            dsn = args.dsn or config.resolved_dsn()
            return run_inspect(
                dsn, args.identifier, reveal=args.reveal, as_json=args.json
            )
        parser.error(f"unknown command {args.command}")
        raise AssertionError("unreachable")  # parser.error exits
    except IrrevonError as err:
        # The §1.3 envelope on the final line of stderr, exit non-zero.
        import json as _json

        print(_json.dumps(err.to_envelope()), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 1


def entrypoint() -> None:  # [project.scripts]
    sys.exit(main())
