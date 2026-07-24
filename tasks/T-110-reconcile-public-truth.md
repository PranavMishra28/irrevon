# T-110: Reconcile public licensing and security truth

---
id: T-110
status: done
depends_on: []
invariant: "ADR-0028: the repository is Apache-2.0 while ADR-0014's contributor-governance half remains open"
---

## Objective
Remove plainly stale pre-license and pre-deployment statements from public repository
guidance, generated third-party notices, and the site's source-code metadata.

## Why
ADR-0028 ratified Apache-2.0 for the whole repository while leaving inbound contribution
governance open. `[VF]` ADR-0027 also records a hosted static marketing site, so public
security guidance must distinguish that static surface from the absent engine/API service.

## Context — read these first
- `AGENTS.md`
- `docs/decisions/0014-licensing.md`
- `docs/decisions/0027-site-vercel-deploy.md`
- `docs/decisions/0028-apache-2-license.md`
- `LICENSING.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `scripts/build-third-party-notices.py`
- `site/src/lib/jsonld.ts`
- `site/e2e/seo.spec.ts`

## Scope
**Allowed to write:** `tasks/T-110-reconcile-public-truth.md`, `CONTRIBUTING.md`,
`SECURITY.md`, `scripts/build-third-party-notices.py`, generated
`THIRD-PARTY-NOTICES.md`, `site/src/lib/jsonld.ts`, and `site/e2e/seo.spec.ts`.

**Forbidden:** contribution mechanisms or issue forms; DCO/CLA policy; feedback or contact
channels; privacy or trademark policy; package-license metadata; analytics; publication;
repository settings; `docs/master-doc.md`; accepted ADR text; schemas; product runtime;
generated site documentation mirrors; and anything not explicitly allowed above.

## Acceptance criteria
- [x] `CONTRIBUTING.md` says the published repository is Apache-2.0 and separately says
      outside code/content contributions remain closed pending human-ratified governance.
- [x] `SECURITY.md` makes private vulnerability reporting conditional on the GitHub feature
      being visible and does not invent a fallback channel.
- [x] `SECURITY.md` distinguishes the hosted static marketing site from the absent hosted
      engine, API, workbench, and production ledger.
- [x] `python3 scripts/build-third-party-notices.py --check` exits 0 and the generated
      notice identifies Apache-2.0 as the project's own license.
- [x] `site/e2e/seo.spec.ts` fails if `SoftwareSourceCode` omits the Apache-2.0 repository
      LICENSE URL, and `make site-test` passes with that assertion.
- [x] `make site-check` and `make check` pass.

## Required validation
```sh
python3 scripts/build-third-party-notices.py --check
make site-check
make site-test
make check
```

## Documentation updates
Update only the public truth surfaces named in Scope; no generated repository-document
mirror is affected because none of the canonical files changed by this task is rendered
through `site/docs-manifest.json`.

## Human review triggers — stop and ask if:
- Correct reporting guidance requires enabling a repository setting or publishing a new
  contact channel.
- Correct contributor guidance requires choosing DCO, CLA, or another inbound mechanism.
- Validation requires an accepted-ADR, product-scope, dependency, analytics, or deployment
  change.

## Definition of done
All criteria checked; validation output attached; documentation updates made; no writes
outside allowed scope; status set.

## Completion record — 2026-07-23
- `python3 scripts/build-third-party-notices.py --check` — notices in sync; every direct
  dependency covered.
- `make site-check` under Node 24.14.0 — Astro reported 0 errors / 0 warnings; all generated
  site assets and content mirrors matched.
- `make site-test` under Node 24.14.0 — 318 passed, including the exact
  `SoftwareSourceCode.license` repository URL assertion.
- `make check` — all validation gates passed.
