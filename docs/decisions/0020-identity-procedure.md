---
id: ADR-0020
title: Ratify the byte-level identity procedure — JCS (RFC 8785) canonical form + SHA-256, operation_id concatenation, key derivation
status: proposed
date: 2026-07-21
supersedes: —
---

## Context

RFC-001 §1 pins the byte-level identity procedure and states that implementing it
requires a short ADR ratifying items 1–4 (master doc §12.5: identity rules are
invariant-affecting). ADR-0013 supplied the encoder/hash pins (`rfc8785` 0.1.4,
version-pinned and vendor-ready; stdlib `hashlib.sha256`) and the cross-implementation
evidence: four independent JCS implementations (Python/Node/Go/Rust) produced
byte-identical canonical output on all shared vectors, including the RFC 8785
number/string torture vector and a non-ASCII key-sorting vector `[VF]` (T-000 spike,
recorded in ADR-0013). T-101 implements the procedure in `src/detent/identity/`.

## Decision

Ratify RFC-001 §1 items 1–4 exactly as written, as the implemented contract:

1. **Canonical form:** the identity tuple is encoded as the JSON object
   `{"effect_type": …, "scope": …, "stable_ids": {…}}` and canonicalized per
   **RFC 8785 (JCS)** — lexicographic member ordering, canonical number/string
   encoding, UTF-8 bytes.
2. **Normalization:** stable-id values are opaque strings, hashed exactly as supplied
   (no case folding); absent optional members are omitted, never null.
3. **Hash:** `intent_id` = lowercase-hex SHA-256 over the canonical UTF-8 bytes.
4. **`operation_id` = `intent_id ‖ ":" ‖ step`**, `step` allocated by the ledger
   (RFC-002 §1 refinement of "workflow-assigned"); idempotency evidence derives
   **only** from `operation_id`.

Implementation pins: `rfc8785==0.1.4` (exact pin, not a floor), guarded by the
committed cross-implementation conformance vectors in `tests/identity/vectors/`
(the four T-000 spike vectors with their cross-language SHA-256 digests as the
external oracle). Any vector failure is a stop-and-ask event, never a re-pin in
place (T-101 human-review trigger).

## Alternatives

- Naive string concatenation of tuple members — rejected: separator-injection
  collisions (`{"a":"b:c"}` vs `{"a:b":"c"}`); property-tested against.
- `json.dumps(sort_keys=True)` as canonical form — rejected: not JCS-conformant on
  number/string edge cases; no cross-language byte agreement.
- Hash of full contract including `parameters` — rejected long ago (ADR-001): breaks
  under re-synthesis; `parameters` is a carrier, never an identity input (ADR-0019).

## Consequences

Every ledger record keys off this procedure; changing it re-keys the ledger
(the least reversible decision in the slice). The M3 conformance tests
(master doc §12.1 row 1) — permutation invariance, model-output independence,
sensitivity, cross-process determinism, pinned vectors — enforce it continuously.

## Risks

`rfc8785` is a near-dormant micro-library (ADR-0013 negative finding 1); the frozen
spec, exact pin, conformance vectors, and vendor-readiness (Apache-2.0) bound the
risk. A silent encoder regression is caught by the vectors before any identity is
mis-derived.

## Reopen trigger

Any committed conformance vector fails to reproduce byte-for-byte under the pinned
encoder; or a destination requires an identity input the three-member tuple cannot
carry (would also reopen ADR-001).
