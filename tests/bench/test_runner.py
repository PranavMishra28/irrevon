"""Runner discipline: write-ahead manifests, duplicate-execution prevention,
interrupted-run finalization + bounded replacement, harness-invalid
classification, pre-freeze integrity refusal, and the BASELINE-STRENGTH LOCKS
(assertion directions that are pinned and never weakened)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from irrevon.bench.fixtures import write_dev_split
from irrevon.bench.formats import load_document, load_fixture_set
from irrevon.bench.runner import (
    IntegrityRefusal,
    refuse_unless_confirmatory_allowed,
    run_unit,
)

RL_WORKLOAD = "wl_dev.c2.responselost.irre.r0"
RESYN_WORKLOAD = "wl_dev.c2.semanticresynthesis.irre.r0"
STORM_WORKLOAD = "wl_dev.c2.retrystorm.irre.r0"


@pytest.fixture(scope="module")
def dev_split(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("fixtures")
    write_dev_split(root)
    return root


def _run(dev_split: Path, out: Path, workload: str, arm: str) -> dict:
    outcome = run_unit(load_fixture_set(dev_split), workload, arm, out)
    assert outcome.status == "completed"
    return json.loads((outcome.run_dir / "result.json").read_text(encoding="utf-8"))


# ── baseline-strength locks (pinned directions; never weakened) ───────────────


def test_lock_b5_duplicates_under_response_lost_on_c2(dev_split: Path, tmp_path: Path) -> None:
    """THE contrast premise (master doc §8.3/§8.6): if B5 stops duplicating on
    C2 under response-lost, the project premise is wrong and this failure must
    SURFACE — never patch this assertion to pass."""
    result = _run(dev_split, tmp_path, RL_WORKLOAD, "B5")
    assert result["metrics"]["duplicate_effect_rate"]["numerator"] >= 1
    assert result["validity"]["status"] == "VALID"


def test_lock_b0_b3_duplicate_under_resynthesis(dev_split: Path, tmp_path: Path) -> None:
    for arm in ("B0", "B3"):
        result = _run(dev_split, tmp_path, RESYN_WORKLOAD, arm)
        assert result["metrics"]["duplicate_effect_rate"]["numerator"] >= 1, arm


def test_lock_b1_defeated_by_resynthesis_not_identical_retry(
    dev_split: Path, tmp_path: Path
) -> None:
    """B1's honest profile: arg-hash dedup suppresses IDENTICAL retries (no
    duplicate under response-lost) but is defeated by re-synthesis."""
    identical = _run(dev_split, tmp_path, RL_WORKLOAD, "B1")
    assert identical["metrics"]["duplicate_effect_rate"]["numerator"] == 0
    resynth = _run(dev_split, tmp_path, RESYN_WORKLOAD, "B1")
    assert resynth["metrics"]["duplicate_effect_rate"]["numerator"] >= 1


def test_lock_composite_is_strong_on_queryable_c2(dev_split: Path, tmp_path: Path) -> None:
    """The preselected composite (B5+B3+B6) legitimately avoids duplicates on
    a fully queryable C2 destination — the ladder is NOT rigged: the composite
    must look strong where it honestly is strong (AM-7 discipline)."""
    for workload in (RL_WORKLOAD, RESYN_WORKLOAD, STORM_WORKLOAD):
        result = _run(dev_split, tmp_path, workload, "B5+B3+B6")
        assert result["metrics"]["duplicate_effect_rate"]["numerator"] == 0, workload


def test_b7_refuses_instead_of_running_a_strawman(dev_split: Path, tmp_path: Path) -> None:
    with pytest.raises(IntegrityRefusal, match="not operationalized"):
        run_unit(load_fixture_set(dev_split), RL_WORKLOAD, "B7", tmp_path)


def test_status_check_arms_degrade_honestly_on_c3(dev_split: Path, tmp_path: Path) -> None:
    """B6 and the composite lose their status-check leg on an opaque
    destination (no query exists): they degrade to their underlying retry —
    which duplicates — instead of crashing or silently claiming detection."""
    for arm in ("B6", "B5+B3+B6"):
        result = _run(dev_split, tmp_path, "wl_dev.c3.responselost.irre.r0", arm)
        assert result["validity"]["status"] == "VALID"
        assert result["metrics"]["duplicate_effect_rate"]["numerator"] >= 1, arm


# ── §6/§8 execution discipline ────────────────────────────────────────────────


def test_write_ahead_manifest_and_result_schema_valid(
    dev_split: Path, tmp_path: Path
) -> None:
    fixture_set = load_fixture_set(dev_split)
    outcome = run_unit(fixture_set, RL_WORKLOAD, "B0", tmp_path)
    manifest = load_document(outcome.run_dir / "run-manifest.json")  # schema-validates
    result = load_document(outcome.run_dir / "result.json")
    assert manifest["confirmatory"] is False
    assert "non-confirmatory" in result["labels"]
    assert result["run_manifest_digest"].startswith("sha256:")
    assert (outcome.run_dir / "environment.json").is_file()
    assert (outcome.run_dir / "journal.jsonl").is_file()


def test_duplicate_execution_prevented(dev_split: Path, tmp_path: Path) -> None:
    fixture_set = load_fixture_set(dev_split)
    first = run_unit(fixture_set, RL_WORKLOAD, "B0", tmp_path)
    assert first.status == "completed"
    second = run_unit(fixture_set, RL_WORKLOAD, "B0", tmp_path)
    assert second.status == "skipped-duplicate"
    assert second.run_dir == first.run_dir


def test_interrupted_run_finalized_invalid_and_replaced(
    dev_split: Path, tmp_path: Path
) -> None:
    """Manifest without result = interrupted. On the next invocation it is
    finalized as harness-INVALID (retained, marked) and a replacement run with
    the SAME seed executes under a new run id."""
    fixture_set = load_fixture_set(dev_split)
    first = run_unit(fixture_set, RL_WORKLOAD, "B0", tmp_path)
    (first.run_dir / "result.json").unlink()  # simulate death mid-run

    second = run_unit(fixture_set, RL_WORKLOAD, "B0", tmp_path)
    assert second.status == "completed"
    assert second.run_dir != first.run_dir

    finalized = json.loads((first.run_dir / "result.json").read_text(encoding="utf-8"))
    assert finalized["validity"]["status"] == "INVALID"
    assert finalized["validity"]["invalid_class"] == "harness-corruption"

    replacement_manifest = json.loads(
        (second.run_dir / "run-manifest.json").read_text(encoding="utf-8")
    )
    assert replacement_manifest["replaces_run_id"] == first.run_dir.name
    assert replacement_manifest["plan"]["seed"] == json.loads(
        (first.run_dir / "run-manifest.json").read_text(encoding="utf-8")
    )["plan"]["seed"]


def test_slot_exhaustion_reports_unresolved_never_drops(
    dev_split: Path, tmp_path: Path
) -> None:
    fixture_set = load_fixture_set(dev_split)
    for _ in range(3):
        outcome = run_unit(fixture_set, RL_WORKLOAD, "B0", tmp_path)
        (outcome.run_dir / "result.json").unlink()
    final = run_unit(fixture_set, RL_WORKLOAD, "B0", tmp_path)
    assert final.status == "unresolved-slot"
    # All three attempts remain on disk, finalized INVALID — never deleted.
    finalized = sorted(tmp_path.glob("run_*/result.json"))
    assert len(finalized) == 3
    for path in finalized:
        assert json.loads(path.read_text())["validity"]["status"] == "INVALID"


def test_seed_mismatch_is_harness_invalid(dev_split: Path, tmp_path: Path) -> None:
    """A workload whose recorded seed disagrees with §3.4 derivation is
    harness-INVALID — scored against no arm."""
    import shutil

    corrupt_split = tmp_path / "corrupt"
    shutil.copytree(dev_split, corrupt_split)
    victim = corrupt_split / "workloads" / f"{RL_WORKLOAD}.json"
    document = json.loads(victim.read_text(encoding="utf-8"))
    document["seed"] = str(int(document["seed"]) ^ 1)
    from irrevon.bench.canonical import artifact_sha256, canonical_json_text, manifest_root_hash

    victim.write_text(canonical_json_text(document), encoding="utf-8")
    manifest_path = corrupt_split / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["artifacts"]:
        if entry["path"] == f"workloads/{RL_WORKLOAD}.json":
            entry["sha256"] = artifact_sha256(document)
    manifest["root_hash"] = manifest_root_hash(manifest["artifacts"])
    manifest_path.write_text(canonical_json_text(manifest), encoding="utf-8")

    outcome = run_unit(load_fixture_set(corrupt_split), RL_WORKLOAD, "B0", tmp_path / "out")
    assert outcome.validity == "INVALID"
    result = json.loads((outcome.run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["validity"]["invalid_class"] == "seed-mismatch"
    assert result["oracle_readback"]["performed"] is False


def test_confirmatory_refused_pre_freeze(dev_split: Path, tmp_path: Path) -> None:
    """No Stage-B freeze record ⇒ confirmatory mode is an integrity refusal.
    This assertion may only ever be updated by the change that lands the
    HUMAN freeze record itself."""
    fixture_set = load_fixture_set(dev_split)
    with pytest.raises(IntegrityRefusal, match="Stage-B freeze record"):
        refuse_unless_confirmatory_allowed(fixture_set)
    with pytest.raises(IntegrityRefusal):
        run_unit(fixture_set, RL_WORKLOAD, "B0", tmp_path, confirmatory=True)


def test_journal_detail_carries_no_fixture_oracle_labels(
    dev_split: Path, tmp_path: Path
) -> None:
    """Anti-cheating: the episode handed to arms (and therefore the journal's
    arm-side detail) never contains the fixture's oracle labels."""
    fixture_set = load_fixture_set(dev_split)
    outcome = run_unit(fixture_set, RL_WORKLOAD, "B6", tmp_path)
    journal = (outcome.run_dir / "journal.jsonl").read_text(encoding="utf-8")
    assert "eligible_for_dispatch" not in journal
    assert '"legitimate"' not in journal
