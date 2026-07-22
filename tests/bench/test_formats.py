"""Format loading: schema enforcement, corrupted-manifest refusal, and the
schema-evolution guard (unknown formats are rejected, never guessed)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from irrevon.bench.canonical import canonical_json_text, manifest_root_hash
from irrevon.bench.fixtures import write_dev_split
from irrevon.bench.formats import (
    FormatError,
    load_document,
    load_fixture_set,
    validate_document,
    verify_manifest,
)


@pytest.fixture()
def dev_split(tmp_path: Path) -> Path:
    write_dev_split(tmp_path)
    return tmp_path


def test_load_fixture_set_round_trip(dev_split: Path) -> None:
    fixture_set = load_fixture_set(dev_split)
    assert fixture_set.workloads
    assert set(fixture_set.schedules) == set(fixture_set.workloads)
    variants = fixture_set.variants_by_id()
    for schedule in fixture_set.schedules.values():
        for injection in schedule["injections"]:
            if injection["fault"] == "semantic-resynthesis":
                assert injection["param"]["variant_id"] in variants


def test_unknown_format_rejected() -> None:
    with pytest.raises(FormatError, match="unknown irrevonbench format"):
        validate_document({"format": "irrevonbench/workload/v99"})


def test_schema_violation_rejected(dev_split: Path) -> None:
    manifest = json.loads((dev_split / "manifest.json").read_text(encoding="utf-8"))
    manifest["split"] = "training"  # not a level of the three-level strategy
    with pytest.raises(FormatError):
        validate_document(manifest)


def test_corrupted_artifact_digest_refused(dev_split: Path) -> None:
    victim = next(iter(sorted((dev_split / "workloads").glob("*.json"))))
    document = json.loads(victim.read_text(encoding="utf-8"))
    document["trials"][0]["parameters"]["note"] = "tampered"
    victim.write_text(canonical_json_text(document), encoding="utf-8")
    with pytest.raises(FormatError, match="digest drift"):
        load_fixture_set(dev_split)


def test_corrupted_root_hash_refused(dev_split: Path) -> None:
    manifest_path = dev_split / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["root_hash"] = "0" * 64
    manifest_path.write_text(canonical_json_text(manifest), encoding="utf-8")
    problems = verify_manifest(dev_split, manifest)
    assert any("root-hash drift" in p for p in problems)


def test_missing_artifact_named_individually(dev_split: Path) -> None:
    victim = next(iter(sorted((dev_split / "workloads").glob("*.json"))))
    victim.unlink()
    manifest = load_document(dev_split / "manifest.json")
    problems = verify_manifest(dev_split, manifest)
    assert any(p.startswith("missing artifact") for p in problems)


def test_missing_schedule_refused(dev_split: Path) -> None:
    """A workload without its fault schedule is unrunnable and must be refused
    at load, not at run time."""
    manifest = load_document(dev_split / "manifest.json")
    keep = [
        a for a in manifest["artifacts"] if not a["path"].startswith("fault-schedules/")
    ]
    for entry in manifest["artifacts"]:
        if entry["path"].startswith("fault-schedules/"):
            (dev_split / entry["path"]).unlink()
    manifest["artifacts"] = keep
    manifest["root_hash"] = manifest_root_hash(keep)
    (dev_split / "manifest.json").write_text(
        canonical_json_text(manifest), encoding="utf-8"
    )
    with pytest.raises(FormatError, match="no fault schedule"):
        load_fixture_set(dev_split)
