# T-120: Reconcile PR 13 and consolidate the private beginner guide

---
id: T-120
status: done
depends_on: [T-119]
invariant: "master doc §6–§9 and §12; preserve fail-closed action handling, evidence truth, and human-only release gates"
---

## Objective
Reconcile PR #13 onto the merged release-readiness baseline, retain only additive worker,
adapter, benchmark, operations, and documentation work, and leave one compact private
beginner guide.

## Why
PR #14 is merged while PR #13 still contains unique product work and now conflicts with
`main`. The combined tree must preserve the newer security, packaging, accessibility, and
truthfulness controls without duplicating generated documentation or overstating the
provider adapters, benchmark evidence, legal posture, or launch readiness.

## Context — read these first
- `docs/master-doc.md` §6–§9 and §12
- `docs/decisions/0034-continuous-worker-and-provider-adapters.md`
- `docs/review-queue.md` items 39–41
- `docs/operations.md`
- `docs/ci.md`
- `LICENSING.md`

## Scope
**Allowed to write:** this task file; files already changed by PR #13 or merged PR #14;
generated site mirrors and registries required by their repository-owned sync commands;
`src/irrevon/adapters/**` and `tests/adapters/**` for fail-closed draft-adapter corrections;
the public documentation entry surfaces (`README.md`, `SECURITY.md`, `CONTRIBUTING.md`,
`LICENSING.md`, `THIRD-PARTY-NOTICES.md`, `ASSETS.md`, and existing `docs/`, `site/`, and
`web/` documentation files); `AGENTS.md` for factual source-map alignment; an optional
repository-owned showcase video asset only after
size, provenance, and packaging checks;
the private `/Users/pranav/Desktop/IRREVON_BEGINNER_GUIDE.md`; and removal of the redundant
private `/Users/pranav/Desktop/Irrevon-Complete-Guide.md`.

**Forbidden:** `docs/master-doc.md`; accepted ADR decision text; frozen preregistration
sections; unrelated repository files; live provider calls; credentials; deployment,
publication, release, merge, repository-setting, visibility, license, or contribution-policy
changes; inventing requirements or representing draft adapters or synthetic evidence as
production qualification.

## Acceptance criteria
- [x] `origin/main` merges without unresolved conflicts and PR #13 reports mergeable.
- [x] Newer PR #14 security, CI, distribution, accessibility, licensing, and scientific-truth
      controls remain present after reconciliation.
- [x] Unique PR #13 worker, adapter, freeze-registration, operational-evidence, and incident
      documentation remains present without stale generated mirrors.
- [x] Draft provider adapters reject unsupported or ambiguous inputs, preserve identity
      fields, and retain response metadata needed for safe retry/reconciliation decisions.
- [x] Exactly one private Irrevon beginner guide remains, is materially more compact, and
      still explains setup, architecture, product behavior, CI/CD, deployment, security,
      licensing, evidence limits, and remaining human gates.
- [x] Public entry documentation is showcase-ready while preserving the repository's
      research-preview, draft-adapter, synthetic-evidence, and human-gate disclosures.
- [x] `make check` passes.

## Required validation
```text
make check
make py-check
make py-test
make py-test-integration
make web-check
make web-test
make web-e2e
make site-check
make site-test
make dist-smoke
git diff --check
gh pr checks 13 --repo PranavMishra28/irrevon
```

## Documentation updates
Reconcile repository truth in the PR #13 documentation set and its generated mirrors. Keep
the private beginner guide outside the repository.

## Human review triggers — stop and ask if:
- Conflict resolution would change product scope, accepted decisions, frozen benchmark text,
  provider terms, licensing, repository settings, or any external/publication action.
- A safe adapter correction requires a provider-specific behavior not already documented by
  the draft declaration or review queue.
- Any guide candidate outside the two named private Irrevon files appears in scope.

## Definition of done
All criteria are checked; validation output is recorded in the PR handoff; no writes occur
outside the declared scope; the redundant guide is recoverably removed; PR #13 is updated
without force-push; and this task is marked `done`.
