# bench/ — IrrevonBench data + run store

Layout (preregistration §8 artifact homes; harness in `src/irrevon/bench/`,
guide in [docs/benchmark.md](../docs/benchmark.md)):

| Path | Contents | Policy |
|---|---|---|
| `fixtures/dev/` | The public development split: workloads, fault schedules, re-synthesis variant sets, manifest — RFC 8785 canonical JSON, rooted by the manifest hash | **Generated, drift-gated.** Regenerate ONLY via `irrevon bench fixtures --write`; CI fails on any divergence from regeneration (`make bench-integrity` + `irrevon bench fixtures --verify` + `tests/bench/test_fixtures.py`). Hand-edits are tampering. |
| `fixtures/` (frozen splits, future) | Stage-B frozen confirmatory artifacts | Land only WITH the human Stage-B freeze record (`docs/registrations/stage-b-v1/`); the integrity gate fails a `frozen` claim without it. |
| `runs/` | The permanent, append-only result store for REGISTERED runs (write-ahead manifests, journals, results incl. INVALID) | Append-only. Local smoke output belongs elsewhere (default `.bench-smoke-runs/`, gitignored). Committing a run directory here is a deliberate, reviewed act. |
| `PUBLISHING.md` | Hugging Face publication preparation (metadata only) | Publication itself is human-gated (execution-plan public-release gate). |

**The sealed holdout is never here** — not in this directory, this repository,
or any agent context (preregistration §7). Only its commitment hashes may ever
be committed. `scripts/check-bench-integrity.py` fails the build on any
holdout-marked artifact, missing canary, digest drift, or premature freeze
claim.

Quick start:

```bash
uv run irrevon bench fixtures --verify      # drift gate
uv run irrevon bench validate --dir bench/fixtures/dev
uv run irrevon bench smoke --out /tmp/runs --arms B0,B1,B3,B5,B6,B5+B3+B6
uv run irrevon bench analyze --runs /tmp/runs --json
```

`irrevon bench run` (confirmatory, M7) refuses with exit 4 until the human
Stage-B freeze exists. That refusal is load-bearing; never weaken it.
