"""Public dev-split fixtures + the holdout sealing mechanism (preregistration §3, §7).

Dev split
    Deterministically generated from ``DEV_MASTER_SEED`` (a PROVISIONAL,
    nothing-up-my-sleeve value: SHA-256 of a documented ASCII string; the public
    dev master seed is frozen — kept or replaced — only by the human Stage-B
    act, review-queue item). Committed under ``bench/fixtures/dev/`` as RFC 8785
    canonical JSON; ``verify_dev_split`` is the drift gate: committed bytes must
    equal regeneration, so neither hand-edits nor silent generator changes can
    slip through.

Holdout mechanism
    ``generate_holdout_shaped_set`` + ``holdout_commitment`` implement the §7
    sealing mechanics (complete labeled artifacts → canonical bytes → plaintext
    root hash → ciphertext hash commitment) and are tested ONLY with explicitly
    synthetic data. They refuse to write inside the repository tree — the
    holdout never enters this repo, any agent context, or any committed file.
    Encryption itself is a documented human step (no key ever exists here).

Dev fault→effect flags (mechanism defaults, not scientific parameters):
pre-dispatch faults (stale-authorization, branch-cancellation) mark the trial
``legitimate=false, eligible_for_dispatch=false`` (a correct arm must abort);
crash-before-persist marks ``legitimate=true, eligible_for_dispatch=false``
(provably effect-free; S-PRE volume near zero per the preregistration §2).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from irrevon.bench.canonical import (
    artifact_sha256,
    canonical_json_text,
    manifest_root_hash,
    sha256_hex,
)
from irrevon.bench.formats import CANARY, load_document, verify_manifest
from irrevon.bench.seeds import derive_seed

__all__ = [
    "DEV_MASTER_SEED",
    "DEV_MASTER_SEED_DERIVATION",
    "build_dev_split",
    "generate_holdout_shaped_set",
    "holdout_commitment",
    "verify_dev_split",
    "write_dev_split",
]

# PROVISIONAL dev master seed (nothing-up-my-sleeve). Freezing or replacing it
# is a §0.1-adjacent human Stage-B act (review-queue item appended by ADR-0030's
# task). Deriving it from a documented string removes any suspicion of seed
# shopping: there is no second candidate that was tried and discarded.
DEV_MASTER_SEED_DERIVATION = "irrevonbench master_seed_dev provisional v1"
DEV_MASTER_SEED = hashlib.sha256(DEV_MASTER_SEED_DERIVATION.encode()).hexdigest()

FAULTS = (
    "crash-before-persist",
    "crash-after-effect-before-response",
    "response-lost",
    "retry-storm",
    "semantic-resynthesis",
    "stale-authorization",
    "branch-cancellation",
)

_FAULT_ANCHOR = {
    "crash-before-persist": "T_FIRST_DURABLE",
    "crash-after-effect-before-response": "T_RESPONSE",
    "response-lost": "T_RESPONSE",
    "retry-storm": "T_DISPATCH",
    "semantic-resynthesis": "T_DISPATCH",
    "stale-authorization": "T_DISPATCH",
    "branch-cancellation": "T_DISPATCH",
}

# Dev-split cell inventory: every fault on the C2 reference destination at the
# IRREVERSIBLE severity, plus the C1 and C3 boundary cells for response-lost.
# All refdest cells are stratum S-REF by construction (disclosed synthetic
# destination-kind; never pooled into confirmatory strata).
_DEV_CELLS: tuple[dict[str, str], ...] = tuple(
    [
        {
            "fault": fault,
            "effect_class": "IRREVERSIBLE",
            "tier": "C2",
            "destination_kind": "refdest",
            "stratum": "S-REF",
        }
        for fault in FAULTS
    ]
    + [
        {
            "fault": "response-lost",
            "effect_class": "IRREVERSIBLE",
            "tier": "C1",
            "destination_kind": "refdest",
            "stratum": "S-REF",
        },
        {
            "fault": "response-lost",
            "effect_class": "IRREVERSIBLE",
            "tier": "C3",
            "destination_kind": "refdest",
            "stratum": "S-REF",
        },
    ]
)

_DEV_REPLICATES = 2
_DEV_TRIALS = 4
# Trials that receive the cell's fault injection (the rest run clean, so rate
# denominators always contain unfaulted trials).
_DEV_FAULTED_TRIALS = (1, 3)


def cell_id_of(cell: dict[str, str]) -> str:
    return f"{cell['tier']}/{cell['destination_kind']}/{cell['fault']}/{cell['effect_class']}"


def _cell_slug(cell: dict[str, str]) -> str:
    fault_slug = cell["fault"].replace("-", "")
    return f"{cell['tier'].lower()}.{fault_slug}.{cell['effect_class'][:4].lower()}"


def _det(seed: int, *parts: object) -> int:
    """Deterministic integer derivation independent of random-module internals."""
    material = ":".join(str(p) for p in (seed, *parts))
    return int.from_bytes(hashlib.sha256(material.encode()).digest()[:8], "big")


def _trial(cell: dict[str, str], seed: int, trial_index: int, fault: str | None) -> dict[str, Any]:
    order_no = 100000 + _det(seed, trial_index, "order") % 900000
    sku = f"SKU-{_det(seed, trial_index, 'sku') % 900 + 100}"
    quantity = _det(seed, trial_index, "qty") % 3 + 1
    legitimate = fault not in ("stale-authorization", "branch-cancellation")
    eligible = legitimate and fault != "crash-before-persist"
    return {
        "trial_index": trial_index,
        "stable_ids": {"order_id": str(order_no), "customer_ref": f"C-{trial_index:04d}"},
        "effect_type": "order.create",
        "scope": "irrevonbench-dev/refdest",
        "parameters": {
            "line_items": [{"sku": sku, "quantity": quantity}],
            "shipping_method": "standard",
            "note": f"benchmark trial {trial_index} (synthetic)",
        },
        "authority_ref": f"auth_bench_{trial_index}",
        "legitimate": legitimate,
        "eligible_for_dispatch": eligible,
    }


def _same_intent_variant(trial: dict[str, Any], variant_id: str) -> dict[str, Any]:
    """Deterministic template re-synthesis: same identity tuple, restructured
    non-identity parameters — the ACRFence failure shape without a model."""
    item = trial["parameters"]["line_items"][0]
    return {
        "variant_id": variant_id,
        "base_workload_id": "",  # filled by the caller
        "base_trial_index": trial["trial_index"],
        "label": "same-intent",
        "stable_ids": dict(trial["stable_ids"]),
        "parameters": {
            "items": [{"sku": item["sku"], "qty": item["quantity"], "gift_wrap": False}],
            "shipping": {"method": "standard", "priority": "normal"},
            "customer_note": f"Benchmark trial {trial['trial_index']} — synthetic retry.",
        },
        "human_verdict": None,
    }


def _generate_unit(
    cell: dict[str, str], replicate: int, master_seed: str, split: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    """(workload, schedule, variants|None) for one cell × replicate."""
    cid = cell_id_of(cell)
    seed = derive_seed(master_seed, cid, replicate)
    slug = _cell_slug(cell)
    workload_id = f"wl_{split}.{slug}.r{replicate}"
    freeze_status = "unfrozen-dev" if split == "dev" else "frozen"

    trials = []
    injections = []
    variants = []
    for t in range(_DEV_TRIALS):
        fault = cell["fault"] if t in _DEV_FAULTED_TRIALS else None
        trial = _trial(cell, seed, t, fault)
        trials.append(trial)
        if fault is None:
            continue
        param: dict[str, Any] = {}
        if fault == "retry-storm":
            param = {"retries": 3}
        elif fault == "semantic-resynthesis":
            variant_id = f"var_{split}.{slug}.r{replicate}.t{t}"
            variant = _same_intent_variant(trial, variant_id)
            variant["base_workload_id"] = workload_id
            variants.append(variant)
            param = {"variant_id": variant_id}
        injections.append(
            {"trial_index": t, "fault": fault, "anchor": _FAULT_ANCHOR[fault], "param": param}
        )

    workload = {
        "format": "irrevonbench/workload/v1",
        "canary": CANARY,
        "workload_id": workload_id,
        "split": split,
        "freeze_status": freeze_status,
        "cell": dict(cell),
        "cell_id": cid,
        "replicate_index": replicate,
        # Decimal string: 64-bit seeds exceed the JCS safe-integer domain.
        "seed": str(seed),
        "trials": trials,
    }
    schedule = {
        "format": "irrevonbench/fault-schedule/v1",
        "canary": CANARY,
        "schedule_id": f"fs_{split}.{slug}.r{replicate}",
        "workload_id": workload_id,
        "split": split,
        "freeze_status": freeze_status,
        "injections": injections,
    }
    variant_set = None
    if variants:
        variant_set = {
            "format": "irrevonbench/variants/v1",
            "canary": CANARY,
            "variant_set_id": f"vs_{split}.{slug}.r{replicate}",
            "split": split,
            "freeze_status": freeze_status,
            "generator": {
                "method": "deterministic-template",
                "model": None,
                "model_version": None,
                "code_ref": "irrevon.bench.fixtures:_same_intent_variant",
                "dedup_method": "canonical-parameter-digest",
            },
            "spot_check": {
                "status": "not-performed",
                "sample_fraction": None,
                "sample_seed": None,
                "cohen_kappa": None,
                "raw_disagreement": None,
                "new_intent_reviewed_fraction": None,
                "disagreements_recorded_at": None,
            },
            "variants": variants,
        }
    return workload, schedule, variant_set


def build_dev_split() -> dict[str, dict[str, Any]]:
    """path → document for the whole committed dev split (manifest included)."""
    files: dict[str, dict[str, Any]] = {}
    artifacts: list[dict[str, Any]] = []

    def add(path: str, document: dict[str, Any]) -> None:
        files[path] = document
        artifacts.append(
            {
                "path": path,
                "artifact_format": document["format"],
                "sha256": artifact_sha256(document),
            }
        )

    for cell in _DEV_CELLS:
        for replicate in range(_DEV_REPLICATES):
            workload, schedule, variant_set = _generate_unit(
                cell, replicate, DEV_MASTER_SEED, "dev"
            )
            add(f"workloads/{workload['workload_id']}.json", workload)
            add(f"fault-schedules/{schedule['schedule_id']}.json", schedule)
            if variant_set is not None:
                add(f"variants/{variant_set['variant_set_id']}.json", variant_set)

    manifest = {
        "format": "irrevonbench/manifest/v1",
        "canary": CANARY,
        "manifest_id": "mf_dev.v1",
        "split": "dev",
        "freeze_status": "unfrozen-dev",
        "master_seed": DEV_MASTER_SEED,
        "generator": {
            "code_ref": "irrevon.bench.fixtures:build_dev_split",
            # Deterministic timestamp: regeneration must be byte-identical.
            "generated_at": "2026-07-22T00:00:00Z",
        },
        "artifacts": sorted(artifacts, key=lambda a: a["path"]),
        "root_hash": manifest_root_hash(artifacts),
        "sealing": None,
    }
    files["manifest.json"] = manifest
    return files


def write_dev_split(root: Path) -> list[str]:
    """Write (or rewrite) the committed dev split; returns the paths written."""
    files = build_dev_split()
    written = []
    for rel, document in sorted(files.items()):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json_text(document), encoding="utf-8")
        written.append(rel)
    return written


def verify_dev_split(root: Path) -> list[str]:
    """Drift gate: committed dev fixtures must byte-match regeneration AND
    self-verify against their manifest. Returns findings (empty = clean)."""
    problems: list[str] = []
    expected = build_dev_split()
    for rel, document in sorted(expected.items()):
        path = root / rel
        if not path.is_file():
            problems.append(f"missing: {rel}")
            continue
        if path.read_text(encoding="utf-8") != canonical_json_text(document):
            problems.append(f"drift vs regeneration: {rel}")
    on_disk = {p.relative_to(root).as_posix() for p in root.rglob("*.json")}
    for extra in sorted(on_disk - set(expected)):
        problems.append(f"unexpected file in dev split: {extra}")
    if not problems:
        manifest = load_document(root / "manifest.json")
        problems.extend(verify_manifest(root, manifest))
    return problems


# ── Holdout sealing mechanism (§7) — synthetic-data-tested, out-of-repo only ──


def _repo_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "docs").is_dir():
            return parent
    return None


def _refuse_in_repo(target: Path) -> None:
    repo = _repo_root()
    if repo is not None and target.resolve().is_relative_to(repo):
        raise PermissionError(
            "holdout artifacts never enter this repository (preregistration §7); "
            f"refusing to write under {repo}"
        )


def generate_holdout_shaped_set(
    target: Path, master_seed: str, *, split: str = "holdout"
) -> dict[str, Any]:
    """Generate a complete holdout-SHAPED artifact set into an out-of-repo
    directory and return its in-archive manifest (which carries the master
    seed and therefore must never leave the sealed archive).

    This is the MECHANISM required by §7; running it with the real holdout
    master seed is a human Stage-B act performed off any agent machine."""
    _refuse_in_repo(target)
    target.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    for cell in _DEV_CELLS:
        for replicate in range(_DEV_REPLICATES):
            workload, schedule, variant_set = _generate_unit(cell, replicate, master_seed, split)
            for sub, document in (
                (f"workloads/{workload['workload_id']}.json", workload),
                (f"fault-schedules/{schedule['schedule_id']}.json", schedule),
            ):
                path = target / sub
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(canonical_json_text(document), encoding="utf-8")
                artifacts.append(
                    {
                        "path": sub,
                        "artifact_format": document["format"],
                        "sha256": artifact_sha256(document),
                    }
                )
            if variant_set is not None:
                sub = f"variants/{variant_set['variant_set_id']}.json"
                path = target / sub
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(canonical_json_text(variant_set), encoding="utf-8")
                artifacts.append(
                    {
                        "path": sub,
                        "artifact_format": variant_set["format"],
                        "sha256": artifact_sha256(variant_set),
                    }
                )
    artifacts.sort(key=lambda a: a["path"])
    in_archive_manifest = {
        "artifacts": artifacts,
        "root_hash": manifest_root_hash(artifacts),
        "master_seed": master_seed,
    }
    (target / "archive-manifest.json").write_text(
        canonical_json_text(in_archive_manifest), encoding="utf-8"
    )
    return in_archive_manifest


def holdout_commitment(
    plaintext_root_hash: str, ciphertext: Path, *, unseal_condition: str, sealed_at: str
) -> dict[str, Any]:
    """The §7 commitment pair that IS committable: ciphertext hash + plaintext
    root hash, wrapped as an irrevonbench/manifest/v1 sealing record. The
    plaintext itself stays out-of-repo; nothing here can reconstruct it."""
    return {
        "ciphertext_sha256": sha256_hex(ciphertext.read_bytes()),
        "plaintext_root_hash": plaintext_root_hash,
        "sealed_at": sealed_at,
        "unseal_condition": unseal_condition,
    }
