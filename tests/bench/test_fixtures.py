"""Dev-split fixtures: byte-stable reproduction, drift detection, seed
consistency, canary presence, and the holdout in-repo refusal (§7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from irrevon.bench.canonical import canonical_json_text
from irrevon.bench.fixtures import (
    DEV_MASTER_SEED,
    DEV_MASTER_SEED_DERIVATION,
    build_dev_split,
    generate_holdout_shaped_set,
    holdout_commitment,
    verify_dev_split,
    write_dev_split,
)
from irrevon.bench.formats import CANARY, load_fixture_set
from irrevon.bench.seeds import derive_seed

REPO_DEV_SPLIT = Path(__file__).resolve().parents[2] / "bench" / "fixtures" / "dev"


def test_dev_master_seed_is_nothing_up_my_sleeve() -> None:
    import hashlib

    assert DEV_MASTER_SEED == hashlib.sha256(DEV_MASTER_SEED_DERIVATION.encode()).hexdigest()


def test_build_is_deterministic_byte_for_byte() -> None:
    first = build_dev_split()
    second = build_dev_split()
    assert set(first) == set(second)
    for path in first:
        assert canonical_json_text(first[path]) == canonical_json_text(second[path])


def test_committed_dev_split_matches_regeneration() -> None:
    """THE drift gate: the committed fixtures must equal regeneration. If this
    fails, either the fixtures were hand-edited (revert them) or the generator
    changed (regenerate + commit together, and treat the change as a
    benchmark-affecting diff per docs/benchmark.md governance)."""
    assert verify_dev_split(REPO_DEV_SPLIT) == []


def test_committed_seeds_recompute_from_master_seed() -> None:
    fixture_set = load_fixture_set(REPO_DEV_SPLIT)
    master = fixture_set.manifest["master_seed"]
    assert master == DEV_MASTER_SEED
    for workload in fixture_set.workloads.values():
        assert int(workload["seed"]) == derive_seed(
            master, workload["cell_id"], workload["replicate_index"]
        )


def test_every_artifact_carries_the_canary() -> None:
    for path, document in build_dev_split().items():
        assert document.get("canary") == CANARY, path


def test_dev_split_never_claims_frozen_or_holdout() -> None:
    for path, document in build_dev_split().items():
        assert document["split"] == "dev", path
        assert document["freeze_status"] == "unfrozen-dev", path


def test_tampered_fixture_is_detected(tmp_path: Path) -> None:
    write_dev_split(tmp_path)
    victim = next(iter(sorted((tmp_path / "workloads").glob("*.json"))))
    document = json.loads(victim.read_text(encoding="utf-8"))
    document["trials"][0]["legitimate"] = False  # oracle-label tampering
    victim.write_text(canonical_json_text(document), encoding="utf-8")
    problems = verify_dev_split(tmp_path)
    assert any("drift" in p for p in problems)


def test_extra_file_in_split_is_detected(tmp_path: Path) -> None:
    write_dev_split(tmp_path)
    (tmp_path / "workloads" / "wl_dev.smuggled.json").write_text("{}", encoding="utf-8")
    problems = verify_dev_split(tmp_path)
    assert any("unexpected file" in p for p in problems)


def test_private_master_seed_split_round_trips(tmp_path: Path) -> None:
    """The company adoption path: a private 64-hex seed yields a structurally
    identical split that self-verifies from its OWN manifest seed, differs in
    content from the public split, and never claims to be it."""
    import hashlib

    private_seed = hashlib.sha256(b"synthetic private company seed").hexdigest()
    write_dev_split(tmp_path, private_seed)
    assert verify_dev_split(tmp_path) == []
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["master_seed"] == private_seed
    assert manifest["manifest_id"] == "mf_dev.private"
    public = build_dev_split()
    assert manifest["root_hash"] != public["manifest.json"]["root_hash"]


def test_private_seed_is_validated(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="64-char"):
        write_dev_split(tmp_path, "not-a-seed")


def test_holdout_generation_refuses_repo_paths(tmp_path: Path) -> None:
    """§7: holdout artifacts never enter this repository — the mechanism
    refuses the write, it does not merely warn."""
    in_repo = REPO_DEV_SPLIT.parent / "holdout-attempt"
    with pytest.raises(PermissionError):
        generate_holdout_shaped_set(in_repo, DEV_MASTER_SEED)
    assert not in_repo.exists()


def test_holdout_mechanism_with_synthetic_seed(tmp_path: Path) -> None:
    """The sealing mechanics run against an EXPLICITLY SYNTHETIC master seed in
    a temp dir: complete artifacts → plaintext root hash → ciphertext hash
    commitment. The real holdout act is human, off any agent machine."""
    import hashlib

    synthetic_seed = hashlib.sha256(b"synthetic holdout mechanism test").hexdigest()
    target = tmp_path / "holdout-shaped"
    manifest = generate_holdout_shaped_set(target, synthetic_seed)
    assert manifest["master_seed"] == synthetic_seed
    assert len(manifest["artifacts"]) > 0
    # Determinism: same seed, same root hash.
    again = generate_holdout_shaped_set(tmp_path / "again", synthetic_seed)
    assert again["root_hash"] == manifest["root_hash"]
    # A different seed yields different content.
    other = generate_holdout_shaped_set(
        tmp_path / "other", hashlib.sha256(b"other").hexdigest()
    )
    assert other["root_hash"] != manifest["root_hash"]

    ciphertext = tmp_path / "sealed.bin"
    ciphertext.write_bytes(b"stand-in ciphertext (encryption is a human step)")
    commitment = holdout_commitment(
        manifest["root_hash"],
        ciphertext,
        unseal_condition="M7 confirmatory start, after Stage-B freeze",
        sealed_at="2026-07-22T00:00:00Z",
    )
    assert commitment["plaintext_root_hash"] == manifest["root_hash"]
    assert len(commitment["ciphertext_sha256"]) == 64
