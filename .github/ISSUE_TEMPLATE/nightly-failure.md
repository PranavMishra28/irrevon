---
name: Nightly validation failure
about: Filed automatically by the nightly workflow when the scheduled suite goes red.
labels: ""
---

## Nightly validation failure

- **Run:** {{RUN_URL}}
- **Started:** {{RUN_DATE}}
- **Commit:** {{SHA}}
- **Evidence artifact:** if the failing job uploaded one, it is on the run page
  (14-day retention — download before triaging later than that).

### Triage protocol

1. Reproduce locally: `make check` for the deterministic gates; for the online
   checks, re-run the failing command from the workflow log. Once property
   suites exist (M3+), reproduce from the printed Hypothesis seed/blob in the
   run log — never from cached state.
2. If the failure is a real invariant violation: fix forward; the failing case
   becomes a regression test. Never weaken the property, its case floor, or any
   gate to get green.
3. If the failure is environmental (runner, network, external link flake): note
   it here, close only after a green manual re-run (`workflow_dispatch` on the
   nightly workflow).
4. Record novel failure modes in `docs/review-queue.md` section 2 if they reveal
   a design gap.

*Filed automatically by the nightly workflow. One open issue at a time; repeat
failures comment here instead of filing duplicates.*
