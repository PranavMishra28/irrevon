# T-124: Reconcile final CI, release, and history truth

---
id: T-124
status: done
depends_on: [T-123]
invariant: "master doc §9 and §12; preserve security, public-history honesty, append-only governance, and human-only external gates"
---

## Objective

Make one narrow truth-consistency correction so CI, release, and public-history
prose matches the active workflows and the bounded evidence of automated scans.

## Why

The final PR audit left obsolete prose about Dependency Review, bootstrap
tooling, and release activation, and its history wording could be read as an
exhaustive PII audit. This task corrects only those statements.

## Context — read these first

- `AGENTS.md`
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `docs/ci.md`
- `docs/security-policy.md`
- `scripts/check-public-data.py`

## Scope

**Allowed to write:** this task file; comments only in
`.github/workflows/ci.yml`; `docs/ci.md`;
`docs/security-policy.md`; their generated `site/src/content/repo-docs/`
mirrors; `scripts/check-public-data.py`; and PR #16 description metadata.

**Forbidden:** every other repository file; product or workflow behavior;
features; design; deployment; publication; tags; releases; provider calls;
repository settings; history rewrite; frozen or append-only artifacts; and
printing, quoting, or reproducing any sensitive historical value.

## Acceptance criteria

- [x] CI prose matches the `dependency-review` job, `ci-required.needs`, and
      PR-event requirement in `.github/workflows/ci.yml`.
- [x] Security prose describes the existing checksum bootstrap and active,
      human-gated release workflow without implying a release exists.
- [x] Public-history prose discloses reachable pre-redaction personal prose and
      the defined-pattern—not exhaustive PII—scope of automation.
- [x] Generated repository-document mirrors have no drift.
- [x] `make check`, `make public-truth`, relevant site drift/static checks, and
      `git diff --check` pass.

## Required validation

```text
make check
make public-truth
make site-check
node site/scripts/sync-docs.mjs --check
git diff --check
```

## Documentation updates

Regenerate the two generated site repository-document mirrors and update PR
#16's description with the corrected history scope and explicit owner choice.

## Human review triggers — stop and ask if

- Any correction would require changing workflow behavior, exposing a
  historical value, rewriting history, or performing an external owner action.

## Definition of done

All criteria are checked; the task is marked done; one signed-off correction
commit is pushed only to PR #16's existing branch; its description is updated;
and both `ci` and the non-publishing `release` workflow succeed.

## Completion evidence — 2026-07-24

- `make check` — passed, including full-history gitleaks, integrity, frozen
  artifacts, public truth, notices, and benchmark integrity.
- `make public-truth` — passed.
- `make site-check` — passed with zero errors and zero warnings; all generated
  documentation, claims, CLI reference, demo, assets, and OG drift gates passed.
- `python3 scripts/check-public-data.py --include-generated` — the defined-pattern
  scan passed and explicitly reported that it is not an exhaustive historical-PII
  audit.
- `node site/scripts/sync-docs.mjs --check`, Actionlint, and
  `git diff --check` — passed.

No historical value was printed or reproduced. No history, repository setting,
deployment, release, tag, package, provider, benchmark, product behavior, or
workflow behavior was changed. Hosted `ci` and non-publishing `release` results
are recorded on PR #16 after this single commit is pushed.
