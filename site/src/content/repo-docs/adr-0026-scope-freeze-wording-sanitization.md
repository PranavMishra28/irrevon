---
title: "Sanitization supersession of ADR-0000's non-goals wording (decision content unchanged)"
sourcePath: "docs/decisions/0026-scope-freeze-wording-sanitization.md"
sourceSha256: "6ae047faa95001a6b88e0c5719e8d112e6a5dbcc8667313f274c611de6909a74"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0026"
  status: "proposed — owner countersign required (sanitization supersession; recorded on the owner's standing sanitization mandate)"
  date: "2026-07-21"
  supersedes: "ADR-0000 (wording of one non-goals bullet ONLY; every decision of ADR-0000 is restated and remains in force)"
---

## Context

ADR-0000 (accepted) records the scope freeze. Its non-goals bullet ends: "no
revenue-bearing activity until written immigration guidance permits it." That is the only
remaining immigration reference in the tracked tree. AM-16 (ratified 2026-07-21) redacted
personal framing from the master doc and replaced it with neutral "external clearances"
wording; review-queue AM-16 and §3 item 13 acknowledged the ADR-0000 residue as
append-only at the time. The owner's current sanitization mandate (DE-1 neutral phrasing
must be the only trace in the current tree) supersedes that earlier acceptance.

ADR-0000 cannot be edited in place: it is `status: accepted`, and the frozen gate
(`scripts/check-frozen.sh` rule 3) fails any non-status-line diff to an accepted ADR.
The sanctioned path is supersession — this ADR.

## Decision

The ADR-0000 scope freeze is restated **verbatim by reference and unchanged in every
respect except one wording substitution** in the non-goals bullet:

- **Old wording (ADR-0000):** "…no revenue-bearing activity until written immigration
  guidance permits it."
- **New wording (canonical from this ADR forward):** "…no revenue-bearing activity until
  **external clearances (master doc §13)** permit it."

Everything else in ADR-0000 — the frozen technical question (master doc §1.2), the
benchmark-first C2-scoped framing (§1.1, §1.3, ADR-009), the binding non-goals (§5.4),
the deliberately-unfrozen implementation choices, the consequences, and the reopen
trigger — is restated here unchanged and remains in force. This is a sanitization
supersession, not a scope change: the substituted wording is exactly the post-AM-16
master-doc §13 formulation, so the decision text and the master doc now say the same
thing.

ADR-0000's status line is updated to record the supersession (the one sanctioned edit to
an accepted ADR), and the decisions index carries both rows. ADR-0000's file is never
deleted (inbound links from the review queue and the execution plan; append-only record).

## Alternatives

- **Edit ADR-0000 in place** — rejected: fails the frozen gate (rule 3); weakening the
  gate to permit it is prohibited.
- **Leave the wording** — rejected by the owner's sanitization mandate: the current tree
  must carry only the neutral phrasing.
- **A review-queue note without a superseding ADR** — rejected: notes do not change which
  text is canonical; only supersession does.

## Consequences

The current tree's canonical scope-freeze wording carries no immigration reference; the
old wording persists in git history and in ADR-0000's file as historical record (same
posture as review-queue §3 item 13). Tasks citing ADR-0000 for the §5.4 hard boundary may
equivalently cite this ADR.

## Risks

Near-duplicate decision records could confuse readers — mitigated: this ADR contains no
new decision, states so in the title, and the index marks the relationship in both rows.

## Reopen trigger

The owner declines the countersign (this ADR is then withdrawn and the queue records the
decline); or a future master-doc amendment changes the §13 clearance formulation this ADR
mirrors.
