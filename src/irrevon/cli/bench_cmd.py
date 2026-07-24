"""``irrevon bench`` — the benchmark harness CLI (RFC-002 §12 deferred slot).

Subcommands:

- ``fixtures``: regenerate or drift-verify the committed public dev split.
- ``validate``: schema + digest verification of a fixture set or document.
- ``smoke``:    non-confirmatory mechanism run of the dev split against the
  operationalized arms (CI regression mode uses a subset; see docs/benchmark.md).
- ``analyze``:  descriptive comparison (+ optional verdict machinery with
  EXPLICIT margins — §0.1 parameters are never defaulted).
- ``run``:      the M7 confirmatory entry point. Pre-freeze it is an
  INTEGRITY REFUSAL (exit 4): no Stage-B freeze record ⇒ no confirmatory run.

Exit codes follow the CLI table: 0 success · 1 unexpected failure · 2 usage ·
3 declared outcome (drift found, smoke contrast failure) · 4 integrity refusal.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from irrevon.cli.config import Config

__all__ = ["add_bench_parser", "run_bench"]


def add_bench_parser(
    sub: argparse._SubParsersAction,  # type: ignore[type-arg]
    common: argparse.ArgumentParser,
) -> None:
    p_bench = sub.add_parser(
        "bench",
        help="IrrevonBench harness (fixtures, validation, non-confirmatory smoke)",
        description=(
            "Develop, validate, and analyze IrrevonBench artifacts. Confirmatory "
            "execution remains refused until the required human freeze verifies."
        ),
        parents=[common],
    )
    bench_sub = p_bench.add_subparsers(dest="bench_command")

    p_fixtures = bench_sub.add_parser(
        "fixtures",
        help="regenerate or verify the committed public dev split",
        description=(
            "Write or deterministically verify a development fixture split."
        ),
    )
    p_fixtures.add_argument(
        "--dir",
        default="bench/fixtures/dev",
        help="fixture-set directory (default: bench/fixtures/dev)",
    )
    p_fixtures.add_argument(
        "--master-seed", default=None,
        help="64-hex master seed for a PRIVATE workload set (company adoption "
             "path: same structure, schemas, and gates as the public split; "
             "never committed here). Default: the public dev seed.",
    )
    mode = p_fixtures.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help="write the deterministic fixture set"
    )
    mode.add_argument(
        "--verify",
        action="store_true",
        help="verify the fixture set against deterministic regeneration",
    )

    p_validate = bench_sub.add_parser(
        "validate",
        help="schema + digest verification of a fixture set",
        description="Validate fixture schemas, manifests, and content digests.",
    )
    p_validate.add_argument(
        "--dir",
        default="bench/fixtures/dev",
        help="fixture-set directory (default: bench/fixtures/dev)",
    )

    p_smoke = bench_sub.add_parser(
        "smoke",
        help="non-confirmatory mechanism run against the dev split",
        description=(
            "Run a non-confirmatory mechanism check against development fixtures."
        ),
    )
    p_smoke.add_argument(
        "--fixtures",
        default="bench/fixtures/dev",
        help="fixture-set directory (default: bench/fixtures/dev)",
    )
    p_smoke.add_argument(
        "--out",
        default=".bench-smoke-runs",
        help="run-output directory (default: .bench-smoke-runs)",
    )
    p_smoke.add_argument(
        "--arms",
        default="B0,B1,B2,B3,B5,B6,B5+B3+B6",
        help="comma-separated arm ids (R requires --dsn / a reachable ledger)",
    )
    p_smoke.add_argument("--workloads", default=None,
                         help="comma-separated workload ids (default: all)")
    p_smoke.add_argument("--dsn", default=None,
                         help="Postgres admin DSN (required for arm R)")
    p_smoke.add_argument("--enrichment-quirk", action="store_true",
                         help="destination stores normalized/enriched payloads "
                              "(attribution-hardening exercise)")
    p_smoke.add_argument(
        "--json", action="store_true", help="emit the comparison as JSON"
    )

    p_conform = bench_sub.add_parser(
        "conform",
        help="declared-vs-observed capability conformance probes (public "
             "adapter surface only)",
        description=(
            "Compare a capability declaration with synthetic reference-destination "
            "observations."
        ),
    )
    p_conform.add_argument("--tier", choices=("C1", "C2", "C3"), default="C2",
                           help="reference-destination profile to probe")
    p_conform.add_argument("--declaration", default=None,
                           help="capability declaration JSON (default: the "
                                "packaged refdest declaration for --tier)")
    p_conform.add_argument("--declared-tier", default=None,
                           help="probe with the declaration of a DIFFERENT tier "
                                "(drift demonstration)")
    p_conform.add_argument(
        "--json", action="store_true", help="emit the conformance report as JSON"
    )

    p_analyze = bench_sub.add_parser(
        "analyze",
        help="descriptive comparison over completed runs",
        description=(
            "Build a descriptive comparison from completed run artifacts."
        ),
    )
    p_analyze.add_argument(
        "--runs", required=True, help="directory containing completed benchmark runs"
    )
    p_analyze.add_argument(
        "--json", action="store_true", help="emit the comparison as JSON"
    )
    p_analyze.add_argument(
        "--verdict", action="store_true",
        help="additionally run the registered verdict machinery (synthetic/mechanism "
             "data only pre-freeze; requires explicit --margin and --worst-cell-gate)",
    )
    p_analyze.add_argument("--margin", type=float, default=None,
                           help="TOST equivalence margin δ (human parameter; no default)")
    p_analyze.add_argument("--worst-cell-gate", type=float, default=None,
                           help="worst-cell gate in absolute rate points (no default)")
    p_analyze.add_argument(
        "--reference-arm", default="R", help="reference arm id (default: R)"
    )
    p_analyze.add_argument(
        "--composite-arm",
        default="B5+B3+B6",
        help="composite comparator arm id (default: B5+B3+B6)",
    )
    p_analyze.add_argument(
        "--b5-arm", default="B5", help="durable-runtime comparator arm id (default: B5)"
    )

    p_run = bench_sub.add_parser(
        "run",
        help="confirmatory benchmark run (refused pre-freeze)",
        description=(
            "Attempt a confirmatory run; refuse unless the human-controlled "
            "freeze registration verifies."
        ),
    )
    p_run.add_argument(
        "--fixtures", required=True, help="frozen fixture-set directory"
    )
    p_run.add_argument(
        "--out", default="bench/runs", help="run-output directory (default: bench/runs)"
    )
    p_run.add_argument(
        "--arms", default=None, help="comma-separated arm ids (default: registered arms)"
    )
    p_run.add_argument(
        "--dsn", default=None, help="Postgres admin DSN when a selected arm requires it"
    )

    p_freeze = bench_sub.add_parser(
        "freeze",
        help="freeze-registration tooling: draft the machine-verifiable "
             "package or verify an existing registration (the freeze act "
             "itself is human-only)",
        description=(
            "Draft freeze bindings or verify an existing human-created "
            "registration. This command never performs the freeze act."
        ),
    )
    p_freeze.add_argument(
        "--stage",
        choices=("A", "B"),
        required=True,
        help="registration stage to draft or verify",
    )
    mode_f = p_freeze.add_mutually_exclusive_group(required=True)
    mode_f.add_argument("--draft-out", default=None,
                        help="write registration.draft.json (bindings filled, "
                             "human fields sentinelled — can never verify)")
    mode_f.add_argument("--verify", action="store_true",
                        help="verify docs/registrations/stage-<s>-v1/registration.json")


def run_bench(args: argparse.Namespace, config: Config) -> int:
    if args.bench_command is None:
        print("usage: irrevon bench {fixtures,validate,smoke,conform,analyze,run,freeze} …",
              file=sys.stderr)
        return 2

    # Benchmark mode marker: with this set, armed test hooks are a startup
    # error (irrevon.testhooks arming rule) — a benchmark process with fault
    # hooks armed is INVALID by construction.
    if args.bench_command in ("smoke", "run"):
        os.environ["IRREVON_BENCH"] = "1"
        from irrevon.testhooks import assert_arming_sane

        assert_arming_sane()

    if args.bench_command == "fixtures":
        from irrevon.bench.fixtures import verify_dev_split, write_dev_split

        root = Path(args.dir)
        if args.write:
            written = write_dev_split(root, args.master_seed)
            kind = "PRIVATE" if args.master_seed else "public dev"
            print(f"bench fixtures: wrote {len(written)} {kind} artifacts under {root}",
                  file=sys.stderr)
            return 0
        problems = verify_dev_split(root)
        if problems:
            for p in problems:
                print(f"bench fixtures: DRIFT - {p}", file=sys.stderr)
            print("bench fixtures: regenerate with `irrevon bench fixtures --write` "
                  "and commit the result together with the generator change",
                  file=sys.stderr)
            return 3
        print("bench fixtures: dev split matches regeneration byte-for-byte",
              file=sys.stderr)
        return 0

    if args.bench_command == "validate":
        from irrevon.bench.formats import FormatError, load_fixture_set

        try:
            fixture_set = load_fixture_set(Path(args.dir))
        except FormatError as err:
            print(f"bench validate: FAIL - {err}", file=sys.stderr)
            return 3
        print(
            f"bench validate: OK - {len(fixture_set.workloads)} workloads, "
            f"{len(fixture_set.schedules)} schedules, "
            f"{len(fixture_set.variant_sets)} variant sets; root hash "
            f"{fixture_set.manifest['root_hash'][:16]}…",
            file=sys.stderr,
        )
        return 0

    if args.bench_command == "smoke":
        return _run_smoke(args)

    if args.bench_command == "conform":
        return _run_conform(args)

    if args.bench_command == "analyze":
        return _run_analyze(args)

    if args.bench_command == "freeze":
        from pathlib import Path as _Path

        from irrevon.bench.freeze import (
            draft_registration,
            render_verification,
            verify_freeze_registration,
        )

        if args.draft_out is not None:
            path = draft_registration(args.stage, _Path(args.draft_out))
            print(
                f"bench freeze: draft written to {path} — bindings computed from "
                "the current tree; REQUIRED-HUMAN fields must be completed, "
                "externally stamped, and committed under docs/registrations/ by "
                "the human (the draft can never verify)",
                file=sys.stderr,
            )
            return 0
        verification = verify_freeze_registration(args.stage)
        print(render_verification(verification), file=sys.stderr)
        return 0 if verification.ok else 3

    if args.bench_command == "run":
        from irrevon.bench.formats import load_fixture_set
        from irrevon.bench.runner import (
            IntegrityRefusal,
            refuse_unless_confirmatory_allowed,
        )

        try:
            fixture_set = load_fixture_set(Path(args.fixtures))
            refuse_unless_confirmatory_allowed(fixture_set)
        except IntegrityRefusal as err:
            print(f"bench run: INTEGRITY REFUSAL - {err}", file=sys.stderr)
            return 4
        # Reaching here requires the human Stage-B freeze record; the
        # confirmatory execution path then reuses run_unit(confirmatory=True)
        # under the frozen plan. Deliberately not implemented further until
        # Stage-B exists (arm-order protocol and trial counts are Stage-B
        # artifacts this code must consume, not invent).
        print(
            "bench run: Stage-B freeze record found, but the confirmatory "
            "execution plan (arm order, trial counts) is a Stage-B artifact "
            "this build does not carry — update the harness against the "
            "frozen plan first (preregistration §0).",
            file=sys.stderr,
        )
        return 4

    raise AssertionError("unreachable")


def _run_smoke(args: argparse.Namespace) -> int:
    from irrevon.bench.analysis import build_comparison, load_runs, render_markdown
    from irrevon.bench.formats import load_fixture_set
    from irrevon.bench.runner import ALL_ARM_IDS, IntegrityRefusal, run_unit

    fixture_set = load_fixture_set(Path(args.fixtures))
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ALL_ARM_IDS]
    if unknown:
        print(f"bench smoke: unknown arms {unknown}; known: {list(ALL_ARM_IDS)}",
              file=sys.stderr)
        return 2
    workload_ids = (
        [w.strip() for w in args.workloads.split(",") if w.strip()]
        if args.workloads
        else sorted(fixture_set.workloads)
    )
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for workload_id in workload_ids:
        if workload_id not in fixture_set.workloads:
            print(f"bench smoke: no workload {workload_id}", file=sys.stderr)
            return 2
        for arm_id in arms:
            try:
                outcome = run_unit(
                    fixture_set, workload_id, arm_id, out_dir,
                    admin_dsn=args.dsn, extra_labels=("smoke",),
                    enrichment_quirk=bool(getattr(args, "enrichment_quirk", False)),
                )
            except IntegrityRefusal as err:
                print(f"bench smoke: INTEGRITY REFUSAL - {err}", file=sys.stderr)
                return 4
            if outcome.validity == "INVALID":
                failures += 1
            print(
                f"bench smoke: {workload_id} × {arm_id}: {outcome.status} "
                f"({outcome.validity or '-'})",
                file=sys.stderr,
            )

    records = load_runs(out_dir)
    comparison = build_comparison(records)
    if args.json:
        print(json.dumps(comparison, indent=2, sort_keys=True))
    else:
        print(render_markdown(comparison))
    return 3 if failures else 0


def _run_conform(args: argparse.Namespace) -> int:
    from pathlib import Path as _Path

    from irrevon.adapters.base import declarations_dir, load_declaration
    from irrevon.adapters.refdest import RefDest, RefdestAdapter
    from irrevon.bench.conformance import verify_declaration

    declared_tier = args.declared_tier or args.tier
    if args.declaration is not None:
        declaration = load_declaration(_Path(args.declaration))
    else:
        declaration = load_declaration(
            declarations_dir() / f"refdest-{declared_tier.lower()}.capability.json"
        )
    refdest = RefDest(seed=7, profile=args.tier)
    adapter = RefdestAdapter(f"refdest-{declared_tier.lower()}", declaration, instance=refdest)
    report = verify_declaration(adapter)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"conformance: {report['adapter_id']} against a {args.tier} destination "
              f"→ {report['verdict']} ({report['mismatch_count']} mismatches)",
              file=sys.stderr)
        for probe in report["probes"]:
            print(
                f"  {probe['verdict']:>12}  {probe['capability']}"
                f"  declared={probe['declared']!r} observed={probe['observed']!r}",
                file=sys.stderr,
            )
    return 0 if report["verdict"] == "conformant" else 3


def _run_analyze(args: argparse.Namespace) -> int:
    from irrevon.bench.analysis import (
        build_comparison,
        confirmatory_machinery,
        load_runs,
        render_markdown,
    )

    records = load_runs(Path(args.runs))
    if not records:
        print(f"bench analyze: no completed runs under {args.runs}", file=sys.stderr)
        return 3
    comparison = build_comparison(records)
    output: dict[str, object] = dict(comparison)
    if args.verdict:
        if args.margin is None or args.worst_cell_gate is None:
            print(
                "bench analyze: --verdict requires EXPLICIT --margin and "
                "--worst-cell-gate — equivalence margins and the worst-cell "
                "gate are §0.1 human freeze parameters; this tool never "
                "defaults them",
                file=sys.stderr,
            )
            return 2
        output["verdict"] = confirmatory_machinery(
            records,
            cells=comparison["cells"],
            reference_arm=args.reference_arm,
            composite_arm=args.composite_arm,
            b5_arm=args.b5_arm,
            margin=args.margin,
            worst_cell_gate_pp=args.worst_cell_gate,
        )
    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(render_markdown(comparison))
        if args.verdict:
            print(json.dumps(output["verdict"], indent=2, sort_keys=True))
    return 0
