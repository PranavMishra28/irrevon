"""``irrevon bench`` CLI: exit-code contract, drift gate, integrity refusal."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _bench(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "irrevon.cli", *args],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=cwd or REPO,
    )


def test_bench_without_subcommand_is_usage_error() -> None:
    proc = _bench("bench")
    assert proc.returncode == 2


def test_fixtures_verify_green_on_committed_tree() -> None:
    proc = _bench("bench", "fixtures", "--verify")
    assert proc.returncode == 0, proc.stderr
    assert "matches regeneration" in proc.stderr


def test_fixtures_verify_detects_drift(tmp_path: Path) -> None:
    write = _bench("bench", "fixtures", "--write", "--dir", str(tmp_path / "dev"))
    assert write.returncode == 0
    victim = next(iter(sorted((tmp_path / "dev" / "workloads").glob("*.json"))))
    document = json.loads(victim.read_text(encoding="utf-8"))
    document["trials"][0]["scope"] = "tampered"
    victim.write_text(json.dumps(document), encoding="utf-8")
    proc = _bench("bench", "fixtures", "--verify", "--dir", str(tmp_path / "dev"))
    assert proc.returncode == 3
    assert "DRIFT" in proc.stderr


def test_validate_green_on_committed_tree() -> None:
    proc = _bench("bench", "validate", "--dir", "bench/fixtures/dev")
    assert proc.returncode == 0, proc.stderr
    assert "root hash" in proc.stderr


def test_smoke_end_to_end_json(tmp_path: Path) -> None:
    out = tmp_path / "runs"
    proc = _bench(
        "bench", "smoke",
        "--fixtures", "bench/fixtures/dev",
        "--out", str(out),
        "--workloads", "wl_dev.c2.responselost.irre.r0",
        "--arms", "B0,B6",
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    comparison = json.loads(proc.stdout)
    assert comparison["format"] == "irrevonbench/comparison/v1"
    assert comparison["confirmatory"] is False
    assert "non-confirmatory" in comparison["labels"]
    assert comparison["run_accounting"]["valid"] == 2


def test_smoke_unknown_arm_is_usage_error(tmp_path: Path) -> None:
    proc = _bench(
        "bench", "smoke", "--fixtures", "bench/fixtures/dev",
        "--out", str(tmp_path), "--arms", "B99",
    )
    assert proc.returncode == 2


def test_run_confirmatory_is_integrity_refusal_exit_4() -> None:
    """Exit 4 pre-freeze — the load-bearing guard. This expectation changes
    ONLY with the human Stage-B freeze record."""
    proc = _bench("bench", "run", "--fixtures", "bench/fixtures/dev")
    assert proc.returncode == 4
    assert "INTEGRITY REFUSAL" in proc.stderr
    assert "Stage-B freeze record" in proc.stderr


def test_conform_matched_stack_is_conformant() -> None:
    proc = _bench("bench", "conform", "--tier", "C2", "--json")
    assert proc.returncode == 0, proc.stderr
    report = json.loads(proc.stdout)
    assert report["format"] == "irrevonbench/conformance/v1"
    assert report["verdict"] == "conformant"


def test_conform_drifted_declaration_exits_3() -> None:
    proc = _bench("bench", "conform", "--tier", "C2", "--declared-tier", "C1", "--json")
    assert proc.returncode == 3
    report = json.loads(proc.stdout)
    assert report["verdict"] == "non-conformant"
    assert report["mismatch_count"] >= 1


def test_smoke_with_enrichment_quirk_stays_valid(tmp_path: Path) -> None:
    """Attribution hardening end-to-end: normalized destination storage, same
    rates, run stays VALID with a consistent metric/history cross-check."""
    out = tmp_path / "runs"
    proc = _bench(
        "bench", "smoke", "--fixtures", "bench/fixtures/dev",
        "--out", str(out), "--workloads", "wl_dev.c2.responselost.irre.r0",
        "--arms", "B0", "--enrichment-quirk", "--json",
    )
    assert proc.returncode == 0, proc.stderr
    result_path = next(out.glob("*/result.json"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["validity"]["status"] == "VALID"
    assert result["history"]["cross_check"] == "consistent"
    assert result["oracle_readback"]["ambiguous_attributions"] == 0
    assert (result_path.parent / "history.json").is_file()
    assert (result_path.parent / "history-verdict.json").is_file()


def test_analyze_verdict_requires_explicit_margins(tmp_path: Path) -> None:
    out = tmp_path / "runs"
    smoke = _bench(
        "bench", "smoke", "--fixtures", "bench/fixtures/dev",
        "--out", str(out),
        "--workloads", "wl_dev.c2.responselost.irre.r0", "--arms", "B0",
    )
    assert smoke.returncode == 0
    proc = _bench("bench", "analyze", "--runs", str(out), "--verdict")
    assert proc.returncode == 2
    assert "human freeze parameters" in proc.stderr
