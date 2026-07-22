"""Machine-verifiable freeze registrations (ADR-0033, proposed).

Before this module, confirmatory mode was gated on the mere EXISTENCE of
``docs/registrations/stage-b-v1/`` — a directory anyone could create. Now a
freeze registration is a structured, hash-binding document
(``irrevonbench/freeze-registration/v1``) that must pass STRUCTURAL AND
CRYPTOGRAPHIC-BINDING verification before confirmatory execution is even
considered:

- the registration binds the exact preregistration bytes (SHA-256), the
  exact analysis-implementation sources (per-file SHA-256 over
  ``REQUIRED_ANALYSIS_PATHS``), the §0.1 human parameters as REQUIRED
  numbers, and — for Stage B — the fixture manifest root hash, the dev
  master seed, and the §7 holdout commitment pair;
- any post-freeze edit to the preregistration or the analysis code breaks
  verification (the preregistration's own no-post-freeze-changes rule,
  enforced mechanically); sanctioned amendments append to the registration's
  ``amendments`` list with the new document hash;
- human placeholders (``REQUIRED-HUMAN``) fail verification, so the DRAFT
  package this module generates is complete mechanism but can never gate
  anything open until a human fills, attests, stamps, and commits it.

Honest boundary (recorded, not hidden): this is the mechanical maximum
available offline — hash binding plus structural attestation fields. It
proves the registration is CONSISTENT with the tree and complete; it cannot
prove WHO created it. The who is governed by policy (creating
``docs/registrations/`` is a human-only act — AGENTS.md, review-queue items
35/38) and by the external stamp evidence the registration must reference
(signed tag / OpenTimestamps / OSF), which reviewers verify out-of-band.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from irrevon.bench.canonical import canonical_json_text
from irrevon.bench.formats import validate_document

__all__ = [
    "FREEZE_FORMAT",
    "HUMAN_SENTINEL",
    "REQUIRED_ANALYSIS_PATHS",
    "FreezeVerification",
    "compute_freeze_bindings",
    "draft_registration",
    "registration_path",
    "verify_freeze_registration",
]

FREEZE_FORMAT = "irrevonbench/freeze-registration/v1"

# The sentinel a draft carries in every human-reserved field; verification
# rejects it wherever it appears.
HUMAN_SENTINEL = "REQUIRED-HUMAN"

# The analysis implementation the freeze binds (preregistration §0 checklist:
# "analysis code for §5 written against synthetic data and content-hashed, so
# the confirmatory analysis is mechanical"). Changing any of these after the
# freeze breaks confirmatory verification until a recorded amendment.
REQUIRED_ANALYSIS_PATHS = (
    "src/irrevon/bench/analysis.py",
    "src/irrevon/bench/stats.py",
    "src/irrevon/bench/metrics.py",
    "src/irrevon/bench/history.py",
    "src/irrevon/bench/oracle.py",
    "src/irrevon/bench/seeds.py",
)

_PREREG_PATH = "docs/benchmark-preregistration.md"


def _default_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "docs").is_dir():
            return parent
    raise FileNotFoundError("repository root not found")


def registration_path(stage: str, repo_root: Path) -> Path:
    if stage not in ("A", "B"):
        raise ValueError("stage must be 'A' or 'B'")
    return (
        repo_root / "docs" / "registrations" / f"stage-{stage.lower()}-v1"
        / "registration.json"
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_freeze_bindings(repo_root: Path | None = None) -> dict[str, Any]:
    """The hashes a registration must bind, computed from the CURRENT tree."""
    root = repo_root or _default_repo_root()
    return {
        "preregistration_sha256": _sha256_file(root / _PREREG_PATH),
        "analysis_code_sha256": {
            rel: _sha256_file(root / rel) for rel in REQUIRED_ANALYSIS_PATHS
        },
    }


def draft_registration(stage: str, out_dir: Path, repo_root: Path | None = None) -> Path:
    """Write ``registration.draft.json``: every mechanical binding filled,
    every human-reserved field sentinelled. The draft can NEVER verify — the
    completing act (fill, attest, external stamp, rename to
    registration.json under docs/registrations/, commit) is human-only."""
    root = repo_root or _default_repo_root()
    bindings = compute_freeze_bindings(root)
    document: dict[str, Any] = {
        "format": FREEZE_FORMAT,
        "stage": stage,
        "registered_by": HUMAN_SENTINEL,
        "registered_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "owner_attestation": (
            f"{HUMAN_SENTINEL}: a written statement that the undersigned human "
            "reviewed the bound preregistration bytes and parameters and "
            "performs this freeze"
        ),
        "external_stamp": {
            "method": "other",
            "reference": f"{HUMAN_SENTINEL}: signed-tag / OpenTimestamps / OSF reference",
        },
        **bindings,
        "parameters": {
            # §0.1 human freeze parameters — the draft deliberately fails
            # schema validation until a human replaces these with numbers.
            "trials_per_cell": HUMAN_SENTINEL,
            "confirmatory_seed_count": HUMAN_SENTINEL,
            "equivalence_margin": HUMAN_SENTINEL,
            "c1_equivalence_margin": HUMAN_SENTINEL,
            "worst_cell_gate_pp": HUMAN_SENTINEL,
        },
        "amendments": [],
    }
    if stage == "B":
        manifest_path = root / "bench" / "fixtures" / "dev" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        document["stage_b"] = {
            "fixture_manifest_root_hash": manifest["root_hash"],
            "master_seed_dev": manifest["master_seed"],
            "holdout_ciphertext_sha256": HUMAN_SENTINEL,
            "holdout_plaintext_root_hash": HUMAN_SENTINEL,
            "adapters": [HUMAN_SENTINEL],
        }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "registration.draft.json"
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


@dataclass(frozen=True)
class FreezeVerification:
    stage: str
    ok: bool
    failures: tuple[str, ...] = ()
    registration: dict[str, Any] | None = field(default=None, compare=False)


def _contains_sentinel(value: object) -> bool:
    if isinstance(value, str):
        return HUMAN_SENTINEL in value
    if isinstance(value, dict):
        return any(_contains_sentinel(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_sentinel(v) for v in value)
    return False


def verify_freeze_registration(
    stage: str, repo_root: Path | None = None
) -> FreezeVerification:
    """Structural + hash-binding verification of one stage's registration."""
    root = repo_root or _default_repo_root()
    path = registration_path(stage, root)
    failures: list[str] = []

    if not path.is_file():
        return FreezeVerification(
            stage, False, (f"no registration at {path.relative_to(root)}",)
        )
    try:
        registration = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        return FreezeVerification(stage, False, (f"unreadable registration: {err}",))
    try:
        validate_document(registration)
    except Exception as err:  # FormatError; kept broad so garbage never passes
        return FreezeVerification(stage, False, (f"schema validation failed: {err}",))

    if registration.get("stage") != stage:
        failures.append(
            f"registration stage {registration.get('stage')!r} != expected {stage!r}"
        )
    if _contains_sentinel(registration):
        failures.append(
            "registration carries REQUIRED-HUMAN sentinels — the human freeze "
            "act has not been performed"
        )

    # Binding 1: the preregistration bytes. Amendments append the new hash;
    # the LAST amendment's hash (or the original when none) must match.
    expected_prereg = registration.get("preregistration_sha256", "")
    for amendment in registration.get("amendments", []):
        expected_prereg = amendment.get("new_preregistration_sha256", expected_prereg)
    actual_prereg = _sha256_file(root / _PREREG_PATH)
    if actual_prereg != expected_prereg:
        failures.append(
            "preregistration bytes do not match the frozen hash "
            f"(bound {str(expected_prereg)[:12]}…, actual {actual_prereg[:12]}…); "
            "post-freeze edits require a recorded amendment"
        )

    # Binding 2: the analysis implementation.
    bound_code = registration.get("analysis_code_sha256", {})
    for rel in REQUIRED_ANALYSIS_PATHS:
        if rel not in bound_code:
            failures.append(f"analysis binding missing for {rel}")
            continue
        actual = _sha256_file(root / rel)
        if actual != bound_code[rel]:
            failures.append(
                f"analysis implementation drifted from the freeze: {rel} "
                f"(bound {str(bound_code[rel])[:12]}…, actual {actual[:12]}…)"
            )

    # Binding 3 (Stage B): fixtures + holdout commitment + dev master seed.
    if stage == "B":
        stage_b = registration.get("stage_b", {})
        manifest_path = root / "bench" / "fixtures" / "dev" / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest["root_hash"] != stage_b.get("fixture_manifest_root_hash"):
                failures.append("fixture manifest root hash does not match the freeze")
            if manifest["master_seed"] != stage_b.get("master_seed_dev"):
                failures.append("dev master seed does not match the freeze")
        else:
            failures.append("no fixture manifest to verify against")

    return FreezeVerification(
        stage, not failures, tuple(failures), registration if not failures else None
    )


def render_verification(verification: FreezeVerification) -> str:
    lines = [
        f"freeze stage {verification.stage}: "
        + ("VERIFIED" if verification.ok else "NOT VERIFIED")
    ]
    lines.extend(f"  - {f}" for f in verification.failures)
    return "\n".join(lines)


def canonical_registration_text(document: dict[str, Any]) -> str:
    """Canonical bytes for external stamping (the human hashes/stamps THIS)."""
    return canonical_json_text(document)
