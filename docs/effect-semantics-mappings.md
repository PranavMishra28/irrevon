# Effect-semantics mappings — capability declarations over existing protocols

**Status:** documentation annex to [ADR-0032](decisions/0032-causal-histories-and-conformance.md)
(proposed). This is deliberately NOT a new standard: standalone API-semantics
vocabularies die unadopted (ALPS's IETF draft expired in 2021; the IETF
`Idempotency-Key` header draft expired 2026-04-18 without RFC status `[VF]`
[datatracker](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)).
Irrevon's [capability declaration](../schemas/capability-declaration.schema.json)
stays the internal contract; this annex documents how it projects onto the
protocols agents actually use, and where those protocols carry nothing at all.
The declaration's differentiator is not the vocabulary — it is that
declarations are designed to be **empirically checked** (`irrevon bench conform`,
declared-vs-observed probes) rather than self-asserted. Current conformance
evidence covers only reference/synthetic destinations; provider drafts remain
unobserved.

Facts verified against primary specs, 2026-07-22. Epistemic labels per master
doc §0.

## What each protocol can express

| Declaration field | MCP (rev 2025-03-26+) | A2A v1.0 (Linux Foundation) | OpenAPI 3.1 | HTTP (RFC 9110) | ACP (OpenAI/Stripe) |
|---|---|---|---|---|---|
| tier C1/C2/C3 | ✗ — `destructiveHint` is a binary, explicitly *untrusted* hint; `reversibleHint` is only a discussion-stage SEP `[VF]` | ✗ | ✗ | ✗ | ✗ (payments-scoped) |
| `idempotency.supported` | ~ `idempotentHint` (advisory bool) | ~ send-message "MAY" dedupe on `messageId` `[VF]` | ✗ (ad-hoc `x-` extensions only) | ~ method-level only (§9.2.2: PUT/DELETE/safe) | ✓ `Idempotency-Key` REQUIRED on POSTs `[VF]` |
| `idempotency.window` | ✗ | ✗ | ✗ | ✗ (vendor docs only: Stripe ≥24 h, Adyen ≥7 d `[VF]`) | ~ ≥24 h retention |
| `idempotency.replay_semantics` | ✗ | ✗ | ✗ | ✗ | ✓ replay + `Idempotent-Replayed` header, 422 on body mismatch, 409 in-flight `[VF]` |
| `queryable {supported, by}` | ✗ | ~ `GetTask` (task state, not effect state) | ✗ | ✗ | ✗ |
| `list_queryable` | ✗ | ~ `ListTasks` | ✗ | ✗ | ✗ |
| `client_ref_field` | ✗ | ~ `messageId` (fixed name, optional dedupe) | ✗ | ~ `Idempotency-Key` (never standardized) | ✓ (the key) |
| `consistency.status_settlement_lag` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `compensation_hook` | ✗ | ✗ | ✗ | ✗ | ✗ |
| `citations` (evidence for every claim) | ✗ | ✗ | ✗ | ✗ | ✗ |

Ancestry worth crediting `[VF]`: W3C WoT Thing Description 1.1
(`ActionAffordance.safe` / `.idempotent` / `.synchronous`) is the closest
standardized ancestor — IoT-scoped booleans without window/replay/recovery
semantics; ALPS defined `safe`/`idempotent` descriptor types and expired.

## Reading the table honestly

- **Boolean effect hints exist everywhere; recovery-relevant parameters exist
  nowhere protocol-neutrally.** Windows, replay behavior, effect-level
  queryability, settlement lag, compensation, and evidence citations — the
  fields reconciliation actually needs (RFC-002 §6) — have no counterpart in
  any surveyed protocol. ACP is the strongest prior art and is
  payments-protocol-specific.
- **Every existing hint is advisory and untrusted by its own spec.** MCP:
  "clients MUST consider tool annotations to be untrusted unless they come
  from trusted servers" `[VF]`. This is precisely the gap the conformance
  verifier addresses: a declaration is worth what its observed behavior
  proves, per probe, with `unverifiable` reported honestly.

## Mapping guidance (per protocol)

- **MCP tools** → declaration seed: `idempotentHint` → `idempotency.supported`
  (unverified until probed); `destructiveHint`/`readOnlyHint` → effect-class
  prior (IRREVERSIBLE-vs-read distinction only); everything else must come
  from the destination's own documentation, cited, then probed. If MCP's
  `reversibleHint` SEP lands, it maps to the effect-class axis the same way.
- **A2A tasks** → the task lifecycle (SUBMITTED→WORKING→terminal, plus
  INPUT/AUTH_REQUIRED `[VF]`) is *task* state, not *effect* state: treat an
  A2A agent as C3 unless it exposes an effect-level query surface; `messageId`
  is a candidate `client_ref_field` where the receiving agent documents
  dedupe.
- **Plain REST** → RFC 9110 method semantics give the *method-level* prior;
  `Idempotency-Key` support is a per-vendor claim requiring a citation (the
  draft expired) and a probe; conditional requests (`If-Match`) are
  concurrency control, not retry safety.
- **OpenAPI** → no signal; `x-` extensions in the wild are conventions to
  cite, never to trust.
- **ACP endpoints** → map directly (required key, documented replay/conflict
  semantics, ≥24 h window) — the one ecosystem where C1 semantics are
  protocol-mandated rather than vendor-optional.

## Non-goals

No new header, no new spec, no MCP fork. If ecosystem contribution ever
becomes worthwhile, the route is the MCP SEP/extension pipeline — as a
contribution informed by conformance evidence, not a competing standard
(review-queue records this as a deliberate rejection; reopen trigger in
ADR-0032).
