---
title: "Machine-verifiable freeze registrations + adapter attribution declarations + site build provenance"
sourcePath: "docs/decisions/0033-verifiable-freeze-and-attribution-declarations.md"
sourceSha256: "b333dd73aaf2c7b50d09367455fd1852e7162d325c22c5ceaffcb8c3d2da1898"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0033"
  status: "proposed"
  date: "2026-07-22"
  supersedes: "—"
---

## Context

The owner's completion directive (2026-07-22) named a real weakness the
foundation carried: confirmatory benchmark mode was gated on the mere
EXISTENCE of `docs/registrations/stage-b-v1/` — "a directory's mere existence
cannot enable confirmatory execution." It further required that real
adapters declare their attribution semantics explicitly (never guessed) and
that the deployed site disclose build provenance.

## Decision

1. **Freeze registrations become verifiable documents**
   (`irrevonbench/freeze-registration/v1`, `src/irrevon/bench/freeze.py`).
   A registration binds, by SHA-256: the exact preregistration bytes, each
   analysis-implementation source file (`REQUIRED_ANALYSIS_PATHS`), the §0.1
   parameters as required numbers, and — Stage B — the fixture manifest root
   hash, the dev master seed, and the §7 holdout commitment pair. It must
   carry a non-sentinel `registered_by`, an `owner_attestation`, and an
   `external_stamp` reference (signed tag / OpenTimestamps / OSF).
   `refuse_unless_confirmatory_allowed` now verifies BOTH stages
   structurally and against the current tree; post-freeze edits to the
   preregistration or analysis code break verification until a recorded
   amendment (`amendments[]`, append-only, records what had been observed).
   `irrevon bench freeze --stage A|B --draft-out|--verify` provides the
   tooling; drafts carry `REQUIRED-HUMAN` sentinels and can never verify.
   **Honest boundary:** hash binding + structural attestation is the
   offline mechanical maximum — it proves consistency and completeness, not
   authorship; authorship stays governed by the human-only policy on
   `docs/registrations/` and by the out-of-band stamp reviewers check.
2. **Attribution declarations** (additive `attribution` block on the
   capability-declaration schema): every destination declares its oracle
   attribution modes, strongest first, from
   {exact, stable-id-projection, metadata, temporal-window, ambiguous,
   impossible} plus the fields read. Optional today for backward
   compatibility; REQUIRED for benchmark use at Stage-B (the registration
   binds declarations via digests on run manifests). Refdest declarations
   updated (C1/C2: exact + stable-id-projection; C3: impossible —
   fixture-truth-only per §2.1 L1). The oracle's never-guess discipline
   (ADR-0032) is thereby a declared, per-destination contract rather than a
   refdest-specific behavior.
3. **Site build provenance**: every page's footer discloses the build
   commit (Vercel `VERCEL_GIT_COMMIT_SHA` at deploy, local git otherwise,
   "unknown" honestly), the build timestamp, and the explicit caveat that a
   static build cannot know whether it still matches the default branch.
   The two newest public-relevant research documents (the benchmark guide
   and the effect-semantics mappings) are rendered on the site through the
   existing drift-gated mirror pipeline.

## Alternatives

- *Cryptographic signature verification of registrations* — rejected for
  now: no key infrastructure exists to verify against offline; a
  signed-git-tag reference in `external_stamp` gives reviewers the same
  assurance out-of-band without inventing key management.
- *Trusting the freeze directory with tightened policy only* — rejected:
  policy without mechanism was exactly the audited weakness.
- *A separate attribution schema* — rejected: attribution is a property of
  the destination contract; it belongs on the capability declaration.

## Consequences

Confirmatory mode is now impossible to enable accidentally or by structural
mimicry without also matching the tree's exact hashes and passing sentinel
checks; analysis-code changes after freeze become mechanically visible; the
`check-bench-integrity` gate's freeze-honesty check upgraded to structural
verification. Conformance tests: `tests/bench/test_freeze.py` (11 tests,
incl. the bare-directory regression pin and the amendment path),
schema example suites, CLI pins.

## Risks

An amendment mechanism is only as honest as its use — amendments record
what was observed, but nothing can force that record to be truthful; that
remains a governance property. The provenance footer's local-git fallback
reports the build checkout's commit, which for a dirty tree is approximate
(the caveat text covers it).

## Reopen trigger

The actual Stage-A freeze act (first real registration exercises the
verifier end-to-end); any decision to add signing-key infrastructure; MCP
SEP adoption of effect-semantics fields (would extend the attribution
block's mapping story).
