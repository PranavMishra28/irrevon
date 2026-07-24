# T-135: Close repository-local launch-site audit findings

---
id: T-135
status: done
depends_on: [T-131]
invariant: "master doc §6–§9 product scope, benchmark boundaries, and security claims remain truthful"
---

## Objective
Correct the repository-local launch-site onboarding, evidence navigation, terminology,
production-smoke, and narrow-screen navigation defects substantiated by T-131.

## Why
The public launch surface must guide a new user through a working source bootstrap,
make claim provenance directly inspectable, use plain language on beginner-facing
pages, and fail closed when a built artifact does not match the intended deployment.

## Context — read these first
- `AGENTS.md`
- `tasks/T-131-hostile-launch-site-accessibility-review.md`
- `README.md` (canonical source quickstart)
- `site/src/pages/index.astro`
- `site/src/components/Source.astro`
- `site/src/data/claims.ts`
- `scripts/site-production-smoke.py`
- `tests/scripts/test_site_production_smoke.py`
- `site/src/layouts/Base.astro`

## Scope
**Allowed to write:**
- this task file
- `site/src/pages/index.astro`
- `site/src/data/claims.ts`
- `site/src/components/Source.astro`
- `site/src/content/guides/getting-started.md`
- `site/src/pages/roadmap.astro`
- `site/src/layouts/Base.astro`
- `site/CLAIMS.md` (mechanically generated only)
- `site/scripts/build-claims-md.mjs`
- focused site tests and styles
- focused claim-generator tests
- `scripts/site-production-smoke.py`
- `tests/scripts/test_site_production_smoke.py`
- `Makefile`
- `site/README.md`
- `site/docs/headers-spec.md`
- focused site provenance tests

**Forbidden:** `README.md`, `SUPPORT.md`, `CONTRIBUTING.md`, issue-template
configuration, other implementation, repository settings, deployment, publication,
commits, tags, and external mutations.

## Acceptance criteria
- [x] Home quickstart exactly follows the working scaffold/export/start/second-init/demo flow.
- [x] Ordinary launch and beginner pages expand or remove unexplained project codes.
- [x] Each evidence link targets the selected generated claim anchor.
- [x] Production smoke requires an explicit exact commit SHA and canonical HTTPS origin.
- [x] Smoke validates canonical/OG/sitemap/robots/assets, rejects legacy launch chrome,
      and checks Vercel CSP/security/version-cache policy.
- [x] The make target cannot run without explicit expected SHA and origin.
- [x] Primary navigation remains accessible and materially more compact at 390/320.
- [x] The disabled-Discussions internal destination is labeled `Contribute`, not
      `Community`, without adding a dead community link.
- [x] Focused tests, build, browser/visual checks, and repository gates pass.

## Required validation
- Focused unit/static tests for smoke and public snippets.
- Site build and focused browser checks.
- Representative 390/320 light/dark and forced-colors inspection.
- `make site-check`
- `git diff --check`

## Documentation updates
- Update site operator documentation for the hardened smoke invocation.
- Update this task with validation evidence and mark it `done`.

## Human review triggers — stop and ask if:
- The fix requires changing community destinations, external settings, deployment,
  publishing, repository history, or any file outside this scope.

## Definition of done
All in-scope T-131 findings are fixed and validated without external mutation; the
task status is `done`.

## Outcome

- Replaced the home quickstart with the exact scaffold, environment export,
  service start, second initialization, doctor, and demo sequence; added a
  contract test that keeps the public onboarding surfaces synchronized.
- Expanded benchmark and destination-tier codes at first use on beginner-facing
  pages without changing the underlying claim registry statements.
- Generated stable named anchors for every claim and made each inline source
  link target its selected claim in the commit-pinned registry.
- Hardened production smoke validation around an explicit deployment commit and
  canonical HTTPS origin, cross-page canonical and Open Graph identity,
  sitemap/robots consistency, referenced assets, retired copy and navigation,
  built CSP, and Vercel security/cache headers.
- Reworked the narrow-screen primary navigation into an accessible, progressive
  menu while preserving visible no-JavaScript navigation. The live internal
  destination is labeled `Contribute`; no disabled Discussions link was added.
- Updated site operator documentation with the explicit, fail-closed smoke
  invocation. No deployment, publication, commit, or external mutation occurred.

Validation:

```text
PASS  production site build with explicit origin, environment, and 40-character SHA
PASS  pnpm test
      388 passed
PASS  SITE_EXPECT_COMMIT=<sha> SITE_EXPECT_ORIGIN=https://irrevon.example make site-production-smoke
PASS  uv run pytest -q tests/scripts/test_site_production_smoke.py tests/scripts/test_site_quickstart_contract.py tests/scripts/test_site_integration_guide.py
      37 passed
PASS  uv run ruff check scripts/site-production-smoke.py tests/scripts/test_site_production_smoke.py tests/scripts/test_site_quickstart_contract.py
PASS  representative 390/320 light and dark screenshots plus forced-colors inspection
PASS  make site-check
PASS  make check
PASS  git diff --check
```
