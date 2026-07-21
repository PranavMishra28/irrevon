"""``detent`` CLI — the four first-slice commands (RFC-002 §12):
``init`` · ``doctor`` · ``demo`` · ``inspect``.

Conventions (dx-api §3.0): data on stdout, messages on stderr; ``--json`` /
``--jsonl`` with ``schema_version``; exit codes 0 success · 1 unexpected
failure · 2 usage · 3 declared outcome · 4 integrity refusal. Zero telemetry,
no update checks, no network beyond the configured adapters and localhost
Postgres (conformance-tested).

Deferred (RFC-002 §12): ``bench smoke``/``bench run`` (M5/M7), operator verbs
(M4), ``serve`` (frontend workstream).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from detent import __version__
from detent.errors import DetentError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="detent",
        description=(
            "Detent — reference reconciliation engine for irreversible "
            "AI-agent actions. Detent makes no network connections except to "
            "the destinations you configure and your own Postgres; there is no "
            "telemetry, no crash reporting, no update checking."
        ),
    )
    parser.add_argument("--version", action="version", version=f"detent {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", help="path to detent.toml", default=None)
    common.add_argument("-q", "--quiet", action="store_true")
    common.add_argument("--no-color", action="store_true")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser(
        "init",
        help="scaffold detent.toml, compose.yaml, .env.example",
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
    p_demo.add_argument("--leg", choices=("detent", "b5", "both"), default="both")
    p_demo.add_argument("--keep", action=argparse.BooleanOptionalAction, default=True,
                        help="retain the demo database for `detent inspect`")
    p_demo.add_argument("--jsonl", action="store_true")

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
        from detent.cli.config import load_config

        config = load_config(args.config)
        if args.command == "init":
            from detent.cli.init_cmd import run_init

            return run_init(
                Path(args.dir), config, force=args.force, as_json=args.json
            )
        if args.command == "doctor":
            from detent.cli.doctor import run_doctor

            return run_doctor(config, probe=args.probe, as_json=args.json)
        if args.command == "demo":
            from detent.cli.demo import run_demo

            seed = args.seed if args.seed is not None else config.demo_seed
            return run_demo(
                config, seed=seed, leg=args.leg, keep=args.keep, jsonl=args.jsonl
            )
        if args.command == "inspect":
            from detent.cli.inspect_cmd import run_inspect

            dsn = args.dsn or config.resolved_dsn()
            return run_inspect(
                dsn, args.identifier, reveal=args.reveal, as_json=args.json
            )
        parser.error(f"unknown command {args.command}")
        raise AssertionError("unreachable")  # parser.error exits
    except DetentError as err:
        # The §1.3 envelope on the final line of stderr, exit non-zero.
        import json as _json

        print(_json.dumps(err.to_envelope()), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 1


def entrypoint() -> None:  # [project.scripts]
    sys.exit(main())
