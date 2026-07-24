# T-123: Final launch truth and security audit

---
id: T-123
status: done
depends_on: [T-122]
invariant: "master doc §6–§9 and §12; preserve scientific honesty, capability-bounded claims, append-only governance, privacy, security, accessibility, and human-only external gates"
---

## Objective

Perform one narrow final audit of the actual PR #16 head, resolve remaining
repository-local truth, governance, release, security, packaging, onboarding,
and generated-documentation defects, and re-establish complete launch evidence.

## Why

The open-source research-preview implementation is complete, but launch-facing
copy, owner governance, tag semantics, provider-origin boundaries, generated
mirrors, and public-history claims require one final sliced hostile review.
This task corrects drift without adding product scope or weakening any gate.

## Context — read these first

- `AGENTS.md`
- `README.md`
- `docs/master-doc.md` §§6–§9, §12, and §13
- `docs/project-status.md`
- `docs/ci.md`
- `docs/security-policy.md`
- `docs/operations.md`
- `docs/release.md`
- `docs/decisions/README.md`
- `docs/review-queue.md`
- `site/README.md`

## Scope

**Allowed to write:** this task file; `AGENTS.md`; `README.md`; `CODEOWNERS`;
public metadata and community files; `docs/` except the forbidden artifacts;
`scripts/`; `tests/`; `site/`; `web/`; `.github/`; `Makefile`; packaging and
generated public documentation mirrors required to resolve a substantiated
finding.

**Forbidden:** `docs/master-doc.md`; rewriting accepted ADR decision text;
deleting or resolving review-queue history; editing frozen preregistration
sections; credentials; live-provider calls; confirmatory experiments;
preregistration freeze; package publication; release/tag creation; deployment;
repository settings; history rewrite; new product scope; invented contacts,
entities, customers, results, qualification, adoption, or production evidence.

## Independent review lanes

1. Documentation and launch-facing truth.
2. Governance, ADR status, CODEOWNERS, and community onboarding.
3. Release engineering, tag semantics, workflow permissions, and DCO.
4. Packaging, PyPI trusted publishing, archive contents, SBOM, and checksums.
5. Runtime security, input limits, traversal, identifiers, logging, and cache.
6. Provider origins, credential forwarding, redirects, and test-only seams.
7. Static-site CSP, privacy, analytics, generated docs, and browser security.
8. Public tree, artifacts, media metadata, and reachable-history evidence.
9. Hostile final cross-slice review of the resulting diff.

## Acceptance criteria

- [x] Launch-facing truth matches the current engine, worker, Workbench,
      benchmark development harness, adapters, deployment posture, and evidence.
- [x] Repository-wide ownership and a deterministic CODEOWNERS check exist
      without requiring impossible self-approval.
- [x] Release documentation and automation consistently require a human-created
      annotated tag plus GitHub artifact attestations, never an unverified
      “signed tag.”
- [x] Proposed ADRs remain proposed, accepted history remains append-only, and
      one concise owner checklist covers implemented-but-proposed decisions.
- [x] Production credentials cannot be sent to arbitrary provider origins;
      synthetic transports remain available only through an explicit test seam.
- [x] Site CSP, analytics, privacy, redirects, limits, traversal, redaction,
      cache, and loopback boundaries are truthfully documented and tested.
- [x] Public-data and history claims match actual scans; any history-only owner
      action is sanitized and no history is rewritten.
- [x] Feedback uses Issues and only links Discussions if the feature is already
      enabled and resolvable.
- [x] Generated site documentation is regenerated and every drift gate passes.
- [x] All completion evidence passes locally. Final PR-head CI is recorded on
      PR #16 after this task commit is pushed.

## Required validation

```text
make launch-audit
make check-all
make site-vrt
make dist-smoke
make release-dry-run
git diff --check
```

## Human review triggers — stop and ask if

- A correction requires an external account, deployment, submission,
  publication, provider call, repository setting mutation, history rewrite, or
  credential.
- A claim cannot be reconciled without changing product scope or scientific
  evidence.
- A frozen or append-only artifact appears wrong.

## Definition of done

All nine review lanes return concrete findings or an explicit no-defect result;
every substantiated repository-local finding is resolved; validation evidence
is recorded; no forbidden external action occurs; this task is marked done; and
all changes are committed and pushed only to the existing PR #16 branch.

## Completion evidence — 2026-07-24

Nine independent or cross-slice review lanes completed. Repository-local
findings were corrected across public truth, owner governance, release/tag
semantics, exact distribution contents, SPDX validation, DCO identity handling,
fixed provider origins, response-size limits, JSON-LD serialization, public
data/history scanning, and generated site mirrors.

Validated on the final local tree:

- `make check` — passed.
- `COMPOSE_PROJECT_NAME=irrevon make check-all` — passed: 467 non-integration
  and 258 integration tests, plus 133 Workbench browser tests.
- `make site-vrt` — passed: 418 screenshots.
- `COMPOSE_PROJECT_NAME=irrevon make dist-smoke` — passed exact wheel and sdist
  manifests, clean installs, worker/serve journeys, and Node-less execution.
- `make release-dry-run` — passed checksums, official SPDX validation, and no
  upload, signing, tagging, or publication.
- `COMPOSE_PROJECT_NAME=irrevon make launch-audit` — passed at `completed`;
  `.scratch/launch-audit.json` records `publishing_actions: false`.
- `python3 scripts/check-public-data.py --include-generated` — passed current,
  generated, media-metadata, DSN, environment-file, and reachable-history
  checks; two already-reachable synthetic regression/task paths are narrowly
  path-allowlisted without recording or printing their values.
- `git diff --check`, generated-doc/claims drift checks, shell syntax, and
  `actionlint .github/workflows/release.yml` — passed.

No provider request, confirmatory benchmark, tag, release, package publication,
deployment, repository-setting mutation, or history rewrite was performed.

Remaining human-only launch actions are explicit rather than hidden: restore
and verify the paused Vercel deployment; review proposed ADR-0020–0022 and
ADR-0030–0034; remove the repository-role ruleset bypass; restrict Actions and
enable SHA-pin plus non-provider secret-pattern enforcement; configure the
protected release environment and pending PyPI Trusted Publisher; and complete
the external clearances, provider sandbox choices, and benchmark freeze gates.
