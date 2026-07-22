"""Machine-verifiable freeze registrations (ADR-0033): binding verification,
sentinel rejection, tamper detection, amendment path, and the regression pin
that a directory's mere existence gates nothing anymore."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from irrevon.bench.fixtures import write_dev_split
from irrevon.bench.formats import load_fixture_set
from irrevon.bench.freeze import (
    HUMAN_SENTINEL,
    REQUIRED_ANALYSIS_PATHS,
    compute_freeze_bindings,
    draft_registration,
    registration_path,
    verify_freeze_registration,
)
from irrevon.bench.runner import IntegrityRefusal, refuse_unless_confirmatory_allowed

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture()
def fake_repo(tmp_path: Path) -> Path:
    """A minimal repository tree the verifier can bind against."""
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (root / "docs" / "benchmark-preregistration.md").write_text(
        "# synthetic preregistration (test)\n", encoding="utf-8"
    )
    for rel in REQUIRED_ANALYSIS_PATHS:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / rel, target)
    write_dev_split(root / "bench" / "fixtures" / "dev")
    return root


def _completed_registration(root: Path, stage: str) -> dict:
    bindings = compute_freeze_bindings(root)
    document: dict = {
        "format": "irrevonbench/freeze-registration/v1",
        "stage": stage,
        "registered_by": "Test human (synthetic)",
        "registered_at": "2026-08-01T00:00:00Z",
        "owner_attestation": (
            "Synthetic test attestation exercising the verification mechanism."
        ),
        "external_stamp": {"method": "signed-git-tag", "reference": "tag test-freeze"},
        **bindings,
        "parameters": {
            "trials_per_cell": 60,
            "confirmatory_seed_count": 10,
            "equivalence_margin": 0.01,
            "c1_equivalence_margin": 0.005,
            "worst_cell_gate_pp": 0.10,
        },
        "amendments": [],
    }
    if stage == "B":
        manifest = json.loads(
            (root / "bench" / "fixtures" / "dev" / "manifest.json").read_text()
        )
        document["stage_b"] = {
            "fixture_manifest_root_hash": manifest["root_hash"],
            "master_seed_dev": manifest["master_seed"],
            "holdout_ciphertext_sha256": "d" * 64,
            "holdout_plaintext_root_hash": "e" * 64,
            "adapters": ["refdest-c2"],
        }
    return document


def _install(root: Path, stage: str, document: dict) -> Path:
    path = registration_path(stage, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


def test_missing_registration_fails(fake_repo: Path) -> None:
    verification = verify_freeze_registration("A", fake_repo)
    assert not verification.ok
    assert any("no registration" in f for f in verification.failures)


def test_bare_directory_gates_nothing(fake_repo: Path) -> None:
    """THE regression pin for the old weakness: an existing directory with
    arbitrary content must not verify."""
    record = fake_repo / "docs" / "registrations" / "stage-b-v1"
    record.mkdir(parents=True)
    (record / "whatever.txt").write_text("frozen, trust me", encoding="utf-8")
    assert not verify_freeze_registration("B", fake_repo).ok
    fixture_set = load_fixture_set(fake_repo / "bench" / "fixtures" / "dev")
    with pytest.raises(IntegrityRefusal, match="failed verification"):
        refuse_unless_confirmatory_allowed(fixture_set, repo_root=fake_repo)


def test_completed_registration_verifies(fake_repo: Path) -> None:
    for stage in ("A", "B"):
        _install(fake_repo, stage, _completed_registration(fake_repo, stage))
        verification = verify_freeze_registration(stage, fake_repo)
        assert verification.ok, verification.failures


def test_sentinel_registration_rejected(fake_repo: Path) -> None:
    document = _completed_registration(fake_repo, "A")
    document["registered_by"] = HUMAN_SENTINEL
    _install(fake_repo, "A", document)
    verification = verify_freeze_registration("A", fake_repo)
    assert not verification.ok
    assert any("REQUIRED-HUMAN" in f for f in verification.failures)


def test_draft_never_verifies(fake_repo: Path) -> None:
    draft = draft_registration("A", fake_repo / "scratch", repo_root=fake_repo)
    assert draft.name == "registration.draft.json"
    document = json.loads(draft.read_text(encoding="utf-8"))
    # Install the untouched draft as if someone tried to activate it.
    _install(fake_repo, "A", document)
    verification = verify_freeze_registration("A", fake_repo)
    assert not verification.ok  # sentinel parameters fail schema validation


def test_preregistration_tamper_detected(fake_repo: Path) -> None:
    _install(fake_repo, "A", _completed_registration(fake_repo, "A"))
    prereg = fake_repo / "docs" / "benchmark-preregistration.md"
    prereg.write_text(prereg.read_text() + "\npost-freeze edit\n", encoding="utf-8")
    verification = verify_freeze_registration("A", fake_repo)
    assert not verification.ok
    assert any("preregistration bytes" in f for f in verification.failures)


def test_amendment_rebinds_the_preregistration(fake_repo: Path) -> None:
    document = _completed_registration(fake_repo, "A")
    prereg = fake_repo / "docs" / "benchmark-preregistration.md"
    prereg.write_text(prereg.read_text() + "\namended content\n", encoding="utf-8")
    document["amendments"] = [
        {
            "amended_at": "2026-08-02T00:00:00Z",
            "new_preregistration_sha256": hashlib.sha256(prereg.read_bytes()).hexdigest(),
            "observed_before_amendment": "no observations existed",
            "note": "synthetic amendment for the mechanism test",
        }
    ]
    _install(fake_repo, "A", document)
    assert verify_freeze_registration("A", fake_repo).ok


def test_analysis_code_drift_detected(fake_repo: Path) -> None:
    _install(fake_repo, "A", _completed_registration(fake_repo, "A"))
    stats = fake_repo / "src" / "irrevon" / "bench" / "stats.py"
    stats.write_text(stats.read_text() + "\n# drifted\n", encoding="utf-8")
    verification = verify_freeze_registration("A", fake_repo)
    assert not verification.ok
    assert any("analysis implementation drifted" in f for f in verification.failures)


def test_stage_b_fixture_binding_detected(fake_repo: Path) -> None:
    document = _completed_registration(fake_repo, "B")
    document["stage_b"]["fixture_manifest_root_hash"] = "0" * 64
    _install(fake_repo, "B", document)
    verification = verify_freeze_registration("B", fake_repo)
    assert not verification.ok
    assert any("fixture manifest root hash" in f for f in verification.failures)


def test_confirmatory_requires_both_stages(fake_repo: Path) -> None:
    _install(fake_repo, "B", _completed_registration(fake_repo, "B"))
    fixture_set = load_fixture_set(fake_repo / "bench" / "fixtures" / "dev")
    with pytest.raises(IntegrityRefusal, match="Stage-A"):
        refuse_unless_confirmatory_allowed(fixture_set, repo_root=fake_repo)
    _install(fake_repo, "A", _completed_registration(fake_repo, "A"))
    # Both registrations verify now, but the DEV fixture manifest is not
    # frozen — the last gate still refuses (freeze honesty end to end).
    with pytest.raises(IntegrityRefusal, match="not frozen"):
        refuse_unless_confirmatory_allowed(fixture_set, repo_root=fake_repo)


def test_real_repo_has_no_registration_and_refuses() -> None:
    """The actual repository must refuse confirmatory mode today."""
    assert not verify_freeze_registration("A", REPO).ok
    assert not verify_freeze_registration("B", REPO).ok
