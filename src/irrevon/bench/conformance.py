"""Capability conformance — declared vs observed destination semantics.

Operationalizes master doc §12.1 row 5 ("capability declarations match
observed behavior") as a mechanism: empirical contract probes exercised
through the PUBLIC adapter surface only — exactly what a real integrator can
reach; no truth API, no control plane — producing a machine-readable
`irrevonbench/conformance/v1` report of declared/observed/verdict rows.

Honest verification boundary (recorded per probe, never silently passed):

- A capability the declaration DENIES often cannot be probed through the
  adapter built on that declaration (e.g. the adapter sends no idempotency
  key when the declaration says unsupported) — those rows report
  ``unverifiable``, not ``match``.
- ``mismatch`` rows are evidence the declaration overstates or understates
  the destination (contract drift, master doc §7.6): a Stage-B/M4 blocker
  for benchmark use of that adapter, and the enterprise capability-drift
  signal for private adapters.
"""

from __future__ import annotations

from typing import Any

from irrevon.adapters.base import Adapter, DispatchOrder
from irrevon.bench import HARNESS_VERSION
from irrevon.errors import CapabilityUnsupported
from irrevon.identity import canonical_digest

__all__ = ["CONFORMANCE_FORMAT", "verify_declaration"]

CONFORMANCE_FORMAT = "irrevonbench/conformance/v1"

_DEADLINE_S = 10.0


def _probe(
    capability: str, declared: Any, observed: Any, verdict: str, evidence: dict[str, Any]
) -> dict[str, Any]:
    return {
        "capability": capability,
        "declared": declared,
        "observed": observed,
        "verdict": verdict,  # match | mismatch | unverifiable
        "evidence": evidence,
    }


def _dispatch(adapter: Adapter, ref: str, payload: dict[str, Any]) -> Any:
    return adapter.dispatch(
        DispatchOrder(
            operation_id=ref,
            effect_type="conformance.probe",
            payload=payload,
            client_ref=ref,
        ),
        _DEADLINE_S,
    )


def verify_declaration(adapter: Adapter, *, probe_prefix: str = "conf") -> dict[str, Any]:
    """Run the empirical contract probes for one adapter + declaration pair."""
    declaration = adapter.declare()
    probes: list[dict[str, Any]] = []
    tier = declaration["tier"]
    queryable_declared = bool(declaration.get("queryable", {}).get("supported"))
    idempotency_declared = bool(declaration.get("idempotency", {}).get("supported"))
    list_declared = bool(declaration.get("list_queryable"))

    # ── 1. Idempotency replay semantics (same key, identical request, twice) ──
    if idempotency_declared:
        ref = f"{probe_prefix}-idem-0"
        payload = {"probe": "idempotency", "n": 1}
        try:
            first = _dispatch(adapter, ref, payload)
            second = _dispatch(adapter, ref, payload)
        except CapabilityUnsupported as err:
            probes.append(
                _probe(
                    "idempotency.supported", True, False, "mismatch",
                    {"note": f"declared dispatch surface refused: {err}"},
                )
            )
        else:
            same_ref = (
                first.destination_ref is not None
                and first.destination_ref == second.destination_ref
            )
            n_found: int | None = None
            if queryable_declared:
                try:
                    answer = adapter.status_query(client_ref=ref, deadline_s=_DEADLINE_S)
                    n_found = answer.n_found
                except CapabilityUnsupported:
                    n_found = None
            honored = same_ref or n_found == 1
            probes.append(
                _probe(
                    "idempotency.supported", True, honored,
                    "match" if honored else "mismatch",
                    {
                        "first_ref": first.destination_ref,
                        "second_ref": second.destination_ref,
                        "effects_for_key": n_found,
                        "note": "declared replay semantics were not observed"
                        if not honored else "identical keyed request replayed, not re-executed",
                    },
                )
            )
    else:
        probes.append(
            _probe(
                "idempotency.supported", False, None, "unverifiable",
                {
                    "note": "the adapter sends no idempotency evidence when the "
                    "declaration denies support — absence of the capability is "
                    "not probeable through this adapter surface"
                },
            )
        )

    # ── 2. Query by client reference ───────────────────────────────────────────
    ref = f"{probe_prefix}-query-0"
    if queryable_declared:
        try:
            created = _dispatch(adapter, ref, {"probe": "query", "n": 2})
            answer = adapter.status_query(client_ref=ref, deadline_s=_DEADLINE_S)
            found = answer.result == "PRESENT" and (answer.n_found or 0) >= 1
            probes.append(
                _probe(
                    "queryable.client_ref", True, found,
                    "match" if found else "mismatch",
                    {"result": answer.result, "n_found": answer.n_found,
                     "created_ref": created.destination_ref},
                )
            )
        except CapabilityUnsupported as err:
            # Either the query OR the declared dispatch surface itself was
            # refused — both are declaration-vs-destination drift.
            probes.append(
                _probe(
                    "queryable.client_ref", True, False, "mismatch",
                    {"note": f"declaration claims this surface; the destination refused: {err}"},
                )
            )
    else:
        try:
            adapter.status_query(client_ref=ref, deadline_s=_DEADLINE_S)
            probes.append(
                _probe(
                    "queryable.client_ref", False, True, "mismatch",
                    {"note": "declaration denies queryability but a status query succeeded"},
                )
            )
        except CapabilityUnsupported:
            probes.append(
                _probe(
                    "queryable.client_ref", False, False, "match",
                    {"note": "query correctly unavailable"},
                )
            )

    # ── 3. Query by destination reference ─────────────────────────────────────
    dispatch_surface_ok = not any(
        p["capability"] == "queryable.client_ref"
        and p["verdict"] == "mismatch"
        and "refused" in str(p["evidence"].get("note", ""))
        for p in probes
    )
    if queryable_declared and dispatch_surface_ok:
        result = _dispatch(adapter, f"{probe_prefix}-dref-0", {"probe": "dref", "n": 3})
        if result.destination_ref is None:
            probes.append(
                _probe(
                    "queryable.destination_ref", True, False, "mismatch",
                    {"note": "dispatch returned no destination reference to query by"},
                )
            )
        else:
            answer = adapter.status_query(
                destination_ref=result.destination_ref, deadline_s=_DEADLINE_S
            )
            found = answer.result == "PRESENT"
            probes.append(
                _probe(
                    "queryable.destination_ref", True, found,
                    "match" if found else "mismatch",
                    {"result": answer.result, "ref": result.destination_ref},
                )
            )

        # ── 4. Authoritative absence (never-created reference) ────────────────
        ghost = f"{probe_prefix}-never-dispatched-{canonical_digest(probe_prefix)[7:19]}"
        answer = adapter.status_query(client_ref=ghost, deadline_s=_DEADLINE_S)
        authoritative = answer.result == "ABSENT"
        probes.append(
            _probe(
                "queryable.authoritative_absence", True, authoritative,
                "match" if authoritative else "mismatch",
                {"result": answer.result,
                 "note": "ABSENT must be an authoritative destination answer, "
                         "never a transport artifact (RFC-002 §6.2 precondition)"},
            )
        )

    # ── 5. List enumeration completeness ──────────────────────────────────────
    if list_declared and not dispatch_surface_ok:
        probes.append(
            _probe(
                "list_queryable.enumeration_complete", True, None, "unverifiable",
                {"note": "declared dispatch surface unavailable; enumeration "
                         "completeness cannot be exercised"},
            )
        )
    elif list_declared:
        created_refs = []
        for n in range(3):
            result = _dispatch(adapter, f"{probe_prefix}-list-{n}", {"probe": "list", "n": n})
            if result.destination_ref is not None:
                created_refs.append(result.destination_ref)
        listed = adapter.list_effects(
            "2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", deadline_s=_DEADLINE_S
        )
        listed_refs = {e.get("destination_ref") for e in listed}
        complete = bool(created_refs) and all(r in listed_refs for r in created_refs)
        probes.append(
            _probe(
                "list_queryable.enumeration_complete", True, complete,
                "match" if complete else "mismatch",
                {"created": len(created_refs),
                 "missing": [r for r in created_refs if r not in listed_refs]},
            )
        )
    else:
        try:
            adapter.list_effects(
                "2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", deadline_s=_DEADLINE_S
            )
            probes.append(
                _probe(
                    "list_queryable.enumeration_complete", False, True, "mismatch",
                    {"note": "declaration denies listing but list_effects succeeded"},
                )
            )
        except CapabilityUnsupported:
            probes.append(
                _probe(
                    "list_queryable.enumeration_complete", False, False, "match",
                    {"note": "listing correctly unavailable"},
                )
            )

    mismatches = [p for p in probes if p["verdict"] == "mismatch"]
    return {
        "format": CONFORMANCE_FORMAT,
        "harness_version": HARNESS_VERSION,
        "adapter_id": adapter.adapter_id,
        "tier": tier,
        "declaration_digest": adapter.declaration_digest(),
        "probes": probes,
        "verdict": "conformant" if not mismatches else "non-conformant",
        "mismatch_count": len(mismatches),
        "note": (
            "Probes exercise the PUBLIC adapter surface only. 'unverifiable' "
            "rows are honest verification boundaries, never treated as "
            "matches. A mismatch is contract drift (master doc §7.6): the "
            "declaration must be corrected and re-cited before benchmark use."
        ),
    }
