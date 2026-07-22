---
title: "Worked example — incident replay to permanent regression"
description: "A complete synthetic walkthrough: compile a payments double-charge incident into a private, drift-gated regression suite; reproduce it against the baseline ladder; keep it permanent in CI; export sanitized evidence."
sourcePath: "docs/incident-replay-example.md"
sourceSha256: "f323c06054068f7f1598b5fa8156e7c50864b3459eebf9ce224c23b8d1ad3056"
syncedAt: "2026-07-22"
section: "Benchmark"
renderTitle: false
---

# Worked example — replaying a payments incident as a permanent regression

A complete, runnable, **synthetic** walkthrough of the incident-to-regression
path (docs/benchmark.md §11; SRE incident→prevention practice). Every command
works against the deterministic reference destination; nothing here touches a
real provider or contains real incident data.

## The incident (synthetic, but the documented shape)

The recurring production shape — Knight Capital's fill-tracking gap,
Stripe's and Temporal's own retry guidance, the 2025 agent incidents — is:

> A payment-creation call succeeded at the destination, the response was
> lost, and the retry path created a **second** charge, because the retry
> carried either no idempotency evidence or re-synthesized arguments the
> destination treated as new.

Suppose your postmortem says: *"order 88231: customer double-charged after a
gateway timeout; the workflow retried with regenerated request parameters."*
That is fault `semantic-resynthesis` (or `response-lost` for identical
retries) against a C2-class destination, at the `T_RESPONSE` anchor.

## 1. Compile the incident class into a private fixture set

Generalize, don't transcribe (prevent the *class*, not the one trace):

```bash
# A private master seed — YOURS, never committed anywhere public.
SEED=$(python3 -c "import secrets; print(secrets.token_hex(32))")
uv run irrevon bench fixtures --write --dir ./private-regressions --master-seed "$SEED"
uv run irrevon bench fixtures --verify --dir ./private-regressions
```

This derives the full fault × tier matrix — including the
`semantic-resynthesis`/C2 and `response-lost`/C2 cells your incident
instantiates — from your seed, deterministically, with the same schemas,
canary, and drift gates as the public split. The incident's specifics
(amounts, identifiers) stay in your postmortem; the fixture encodes the
failure *mechanics*.

## 2. Reproduce the incident mechanics (your current strategy vs the ladder)

```bash
uv run irrevon bench smoke --fixtures ./private-regressions --out ./runs \
  --workloads wl_dev.c2.semanticresynthesis.irre.r0,wl_dev.c2.responselost.irre.r0 \
  --arms B0,B1,B2,B3,B5,B6,B5+B3+B6
uv run irrevon bench analyze --runs ./runs --json > incident-comparison.json
```

Pick the arm that matches your current retry strategy (naive retry = B0;
arg-hash dedup = B1; agent-minted keys = B2; stable op-IDs = B3; durable
runtime + keys = B5). Its non-zero `duplicate_effect_rate` on these cells IS
your incident, reproduced under a seeded fault schedule and proven by
destination read-back — with the causal history (`runs/*/history.json`)
showing the exact H1-duplicate-effect violation and the events around it.
Compare against B5+B3+B6 (status-check-before-retry) and, with a Postgres
handy, arm R (`--arms R,B5 --dsn …`).

## 3. Make it permanent

- **Fast CI mode**: pin the two workloads + your arm in a CI job and assert
  the expected verdicts — e.g. "our strategy still duplicates here (known
  gap, tracked)" or, after a fix, "duplicate_effect_rate numerator == 0".
  The run exits non-zero on INVALID runs; your assertion runs on
  `incident-comparison.json` (machine-readable, `irrevonbench/comparison/v1`).
- **Scheduled deep suite**: the full matrix over all replicates plus arm R,
  nightly (`bench smoke` over all workloads).
- **Regression discipline**: the fixture set is drift-gated against your
  seed — nobody can quietly soften the scenario; a generator upgrade
  regenerates visibly and your assertions re-run.

## 4. Export sanitized evidence

Every run directory is already a sanitized, independently verifiable
bundle: write-ahead run manifest, environment manifest, digest-only journal,
compiled causal history + checker verdict, and the result document whose
metrics were cross-checked by two independent oracles. Nothing in it
contains payloads or credentials; hand the directory (or just
`incident-comparison.json`) to auditors, CI, or a policy engine as-is.

## Boundary notes (honest)

Synthetic destination ⇒ these runs demonstrate *mechanics*, not provider
behavior (`synthetic-destination` label is in every result). Replaying
against your real destination's **sandbox** requires the credential-gated
adapter path (declaration + `irrevon bench conform` first) and your own
ToS/rate-budget review. If your incident involves a capability the
declaration cannot express, that is a finding about the declaration —
extend it via the ADR process, don't approximate silently.
