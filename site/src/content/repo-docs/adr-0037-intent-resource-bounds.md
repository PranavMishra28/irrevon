---
title: "Intent validation refuses inputs outside bounded JSON and JCS domains"
sourcePath: "docs/decisions/0037-intent-resource-bounds.md"
sourceSha256: "33f389b5d0cd94d4d578c9f2bde9344380c208a49f0c82f3d9cccc77f0b819f7"
syncedAt: "2026-07-24"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0037"
  status: "accepted"
  date: "2026-07-23"
  supersedes: "—"
---

## Context

The intent contract is the only model-generated input channel into the
deterministic core. JSON Schema validated member types but did not bound nesting,
node count, string size, identifier count, or RFC 8785's safe integer domain.
Schema-valid values could therefore cause recursion failure, encoder-domain
exceptions, excessive memory use, or unbounded persistence before a typed
refusal.

## Decision

Validation performs a non-recursive preflight before JSON Schema or
canonicalization. The entire document is limited to depth 32, 10,000 JSON
nodes, and 1 MiB of scalar/key UTF-8 data; individual strings and keys are
limited to 64 KiB; integers must be in the I-JSON interoperable range
`[-(2^53-1), 2^53-1]`; floats must be finite. The schema additionally bounds
stable-ID cardinality and launch-facing identity strings.

Every preflight, schema, and canonicalization-domain failure maps to
`ContractInvalid`. No ledger row, dispatch claim, or wire attempt may occur.

## Alternatives

- **Rely on request-size limits:** rejected because SDK callers do not cross
  HTTP and deeply nested small documents still exhaust recursion.
- **Let encoder exceptions escape:** rejected because the trust boundary must
  return one typed refusal contract.
- **Unlimited arbitrary JSON:** rejected because recovery stores parameters and
  must have a defensible capacity bound.

## Consequences

Some previously schema-valid but operationally unsafe documents are refused.
Adapters may impose stricter effect-specific limits before persistence; these
generic limits are only the outer safety envelope.

## Risks

The 1 MiB envelope may be too large for some destinations and too small for a
future legitimate effect. Revisit through a new ADR with measured workloads,
storage capacity, and provider limits rather than silently raising it.

## Reopen trigger

A qualified adapter requires a larger payload, or production evidence shows
these limits are insufficient to protect latency/memory/storage budgets.
