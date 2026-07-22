---
id: ADR-0028
title: Outbound license — Apache-2.0 for the whole repository (resolves the license half of ADR-0014)
status: accepted (owner ratification by direct written instruction, 2026-07-21)
date: 2026-07-21
supersedes: — (resolves the license-choice question ADR-0014 held open; ADR-0014's contributor-governance half remains open)
---

## Context

ADR-0014 held the outbound-license decision open with two candidates: **A**
(neutrality-first — Apache-2.0 for everything) and **B** (protection-first — AGPL-3.0
engine + Apache-2.0 harness/schemas/SDK). The master doc assumed Apache-2.0 (§10, §15/M2;
AM-19 marked that assumption subordinate to ADR-0014). On 2026-07-21 the owner ratified
**Candidate A — Apache-2.0** by direct written instruction, understanding explicitly that
the repository is public, so adding the license open-sources it immediately `[DD]`. This
is the human decision review-queue items 7/18 were waiting on; per the review-queue
policy, the queue rows themselves are annotated only by appended records (item 30) —
resolution marks are human acts.

## Decision

The repository is licensed **Apache-2.0** as a whole: the verbatim license text ships as
the root [`LICENSE`](../../LICENSE), with a root [`NOTICE`](../../NOTICE) carrying the
attribution line "Irrevon — Copyright 2026 Irrevon contributors" (a named public notice,
per ADR-0014's consequence 4 that "the repository owner" is not a valid public copyright
notice; the neutral collective name avoids personal identifiers by the standing
sanitization mandate). [`LICENSING.md`](../../LICENSING.md) becomes the short posture
notice for the new state. **Deliberately not included** (each remains a human step on
ADR-0014's consequences ladder): CONTRIBUTING.md / DCO / CLA (contributions stay closed —
the contributor-governance half of ADR-0014 is still open), TRADEMARKS.md and the USPTO
filing (ride the counsel name screen), the CC-BY-4.0 dataset question (no standalone
dataset artifacts exist yet), US copyright registration, counsel review of the adopted
text, and packaging license metadata (SPDX expression + classifier land with the ADR-0018
M8 release mechanics).

## Alternatives

- **Candidate B (AGPL engine + Apache harness hybrid)** — ADR-0014's protection-first
  option; not chosen by the owner. It also carried the recorded structural cost
  (review-queue §3 item 24): the ADR-0018 single wheel violates B's arm's-length
  invariant, forcing a package split or module firewall. A has no such cost.
- **MIT** — equal adoption ceiling but no patent grant; Apache-2.0 §3 matters for an
  engine adjudicating irreversible actions.
- **Source-available (BSL/FSL/ELv2)** — delivers fork-prohibition at fatal cost to
  benchmark neutrality and the open-source claim (ADR-0014 analysis); never a candidate
  at this gate.
- **Stay unlicensed until the public-release gate** — ADR-0014's interim; ended by the
  owner's ratification (an unlicensed public repo destroys adoption and has no inbound
  basis — one-way door 3).

## Consequences

- The published repository is open-source effective immediately; the grant on published
  versions is irrevocable (ADR-0014 one-way door 1 — knowingly taken by the owner).
- Attribution survives every fork via Apache-2.0 §4(c)–(d) NOTICE reproduction — the
  imprint mechanism ADR-0014 identified as fully achievable.
- **Contributions remain closed.** Inbound governance (DCO enforcement, engine
  contribution policy) must land before the first outside PR (ADR-0014 one-way door 2).
- psycopg (LGPL-3.0-only) remains the single non-permissive runtime dependency; the
  recorded analysis (review-queue §2) finds it compatible with Apache-2.0 in the standard
  separately-installed-library way; the documented-exception ruling is still owed
  (rides review-queue items 7/18's residue).
- The master doc's §10/§15 Apache-2.0 assumption is now confirmed rather than
  subordinate; AM-19's text integration proceeds in that direction (queue item 30).
- Conformance: `make check` link/integrity gates cover the new files; the site's
  licensing prose and claims registry are updated in the same change.

## Risks

If a deep-pocketed party ever hosts a commercial Irrevon, Apache-2.0 offers no recourse —
accepted knowingly (ADR-0014's Candidate-A risk, unchanged). Counsel has not yet reviewed
the adoption; ADR-0014's "not legal advice" banner applies to this record too, and the
counsel-review consequence stays on the human ladder.

## Reopen trigger

Counsel review contradicts the adoption's mechanics (text, NOTICE form, or the psycopg
exception); the SFC v. Vizio verdict or an equivalent shift makes the license landscape
materially different before first packaged release; or the owner orders a change for
future versions (published versions stay Apache-2.0 forever — relicensing honesty per
ADR-0014).
