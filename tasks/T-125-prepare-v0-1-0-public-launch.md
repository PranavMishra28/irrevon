# T-125: Prepare the v0.1.0 public-launch candidate

---
id: T-125
status: blocked-human-review
depends_on: [T-124]
invariant: "master doc §5.4, §8, §9, §12, and §13 truth, safety, benchmark-integrity, and human-release gates"
---

## Objective
Prepare one reviewable, non-publishing v0.1.0 launch-candidate pull request whose
repository, package, community, site, dependency, and validation surfaces are
internally consistent and whose remaining human-only blockers are explicit.

## Why
The open-source preparation PR landed, but the current default branch still
contains pre-release package metadata, five separate routine Dependabot lanes,
internal-governance language on product pages, no deployment-version endpoint,
and no GitHub Discussions path. Publication and production deployment remain
blocked by the repository's historical-privacy disclosure and master-doc §13
human gates.

## Context — read these first
- `AGENTS.md`
- `docs/master-doc.md` §5.4, §8, §9, §12, §13
- `docs/project-status.md`
- `docs/security-policy.md`
- `docs/ci.md`
- `docs/release-process.md`
- `site/README.md`
- `.github/workflows/release.yml`

## Scope
**Allowed to write:** this task file; `README.md`; `PACKAGE_README.md`;
`CHANGELOG.md`; `CITATION.cff`; `pyproject.toml`; `src/irrevon/__init__.py`;
`Makefile`; `SUPPORT.md`; `CONTRIBUTING.md`; `.github/dependabot.yml`;
`.github/ISSUE_TEMPLATE/config.yml`; `.github/workflows/release.yml`;
`docs/ci.md`; `docs/security-policy.md`; `docs/project-status.md`;
`docs/project-status.json`; `docs/release-process.md`; `docs/operations.md`;
`docs/discoverability.md`; matching generated files under
`site/src/content/repo-docs/`; repository-local scripts and tests needed to
validate those surfaces; and `site/**`.

**Forbidden:** `docs/master-doc.md`; accepted ADR decision content; frozen
preregistration sections; trust-boundary schemas; live-provider or confirmatory
execution; historical-value reproduction; history rewrite; external settings;
Discussion creation; deployment; tagging; package/release publication; and any
claim that an owner-only action has completed when read-back does not prove it.
Anything else is out of scope.

## Acceptance criteria
- [x] Package and release-candidate metadata agree on `0.1.0`, retain the Alpha
      classifier, and pass wheel/sdist content, clean-install, SBOM, and
      non-publishing release checks.
- [x] The release workflow refuses stale, lightweight, mismatched, fork,
      non-owner, pull-request, and manual publication paths.
- [x] Dependabot defines one monthly multi-ecosystem routine group, preserves
      per-ecosystem security remediation, blocks routine frontend/site majors,
      assigns/labels the owner path, and documents quarterly major review.
- [x] Ordinary product pages use compact product navigation/footer and
      human-readable clickable evidence disclosures while machine/reference
      records retain technical provenance.
- [x] `/version.json` reports release version, full commit, build timestamp,
      benchmark schema/harness version, and deployment environment, and refuses
      malformed production provenance.
- [x] While Discussions remains disabled, public surfaces expose no dead
      Discussion links; the exact owner activation/category/read-back gate and
      private vulnerability route are documented without inventing an email,
      comment database, or support SLA.
- [x] Public truth continues to disclose the unfinished scientific benchmark,
      draft provider adapters, unsupported production topology, and unresolved
      historical-privacy/human release blockers.
- [x] Edge case: a release or production smoke path fails closed when the tag,
      intended SHA, deployed SHA, origin, version, or external release state
      disagrees.
- [x] `make check` passes.

## Required validation
`make check`; `make public-truth`; `make check-all`; `make web-vrt`;
`make site-check`; `make site-build`; `make site-test`; `make site-vrt`;
`make dist-smoke`; `make release-dry-run`; `make launch-audit`;
`actionlint .github/workflows/*.yml`; `zizmor --persona=pedantic
.github/workflows/`; `gitleaks git --redact -v .`; `python3
scripts/check-public-data.py --include-generated`; package-manager vulnerability
audits; exact archive inspection; `git diff --check`; clean-worktree read-back;
and GitHub check read-back after push.

## Documentation updates
Update the public release, community, dependency, security, deployment, and
remaining-owner-action surfaces in scope; regenerate every site mirror and
generated claim/CLI/document artifact affected by those changes.

## Validation evidence — 2026-07-24

- Node `24.18.0` was used for every Node-based release gate.
- `make check`, `make public-truth`, `make check-all`, and the complete
  non-publishing `make launch-audit` ladder passed. The final audit covered 539
  non-integration and 258 PostgreSQL integration/crash tests, 92 Workbench unit
  tests, 80 component stories, 133 browser/accessibility tests, five
  real-service browser tests, 98 pinned Linux visual regressions, the benchmark
  smoke matrix, 388 marketing-site static/browser checks, and 697 route/theme/
  viewport/reduced-motion/forced-color screenshots.
- The production-built static artifact passed exact commit, origin,
  `/version.json`, canonical/SEO, CSP, header, asset, sitemap, robots, and
  retired-copy smoke checks. This is artifact evidence, not a claim that the
  currently deployed Vercel alias is fresh.
- Wheel and sdist exact-content checks, clean Node-less installs, the complete
  packaged CLI/demo/serve/worker journey, SPDX SBOM validation, checksums, and
  the non-publishing release dry run passed.
- The frozen hash-bearing Python production graph and both JavaScript
  production graphs reported no known vulnerabilities. Actionlint, pedantic
  offline zizmor, current-tree and 146-commit gitleaks scans, generated/archive
  scans, public-data checks, generated-content drift checks, and
  `git diff --check` passed.
- Automated history checks cover defined patterns and are explicitly not proof
  that all historical personal information is absent.

## Remaining owner actions

Repository-local work is complete. Launch publication remains blocked until the
owner performs and reads back these human-only choices and settings:

1. Knowingly accept the documented reachable-history exposure, or coordinate a
   complete human-only history rewrite and public-ref replacement, then rescan.
2. Complete the legal/name-clearance and independent-review gates in master doc
   §13.
3. Remove or narrowly constrain the repository-role ruleset bypass and harden
   the required-review, conversation-resolution, and strict/up-to-date-check
   posture without locking the sole owner out.
4. Enable the intended Actions allowlist and platform SHA enforcement; enable
   non-provider secret patterns/validity checks where available; verify the
   grouped-security-updates repository toggle.
5. Enable Discussions; create Announcements, Q&A, Ideas and feedback, and Show
   and tell; publish the reviewed welcome post; read back the canonical URLs;
   only then enable the prepared public Community links.
6. Create and protect `release`, `sandbox`, and `benchmark`; protect
   `Production`; enable immutable releases.
7. Immediately before release, confirm the PyPI name and configure the pending
   OIDC Trusted Publisher plus owner-approved `release` environment.
8. After this PR is reviewed and merged, create the annotated version tag and
   allow the protected workflow to publish PyPI/GitHub artifacts; then deploy
   the exact released commit and pass the production smoke/read-back.

## Human review triggers — stop and ask if:
- Publication, tagging, release creation, deployment, repository settings,
  Discussion creation, legal/name clearance, provider selection, scientific
  freeze/execution, or history rewrite becomes necessary.
- A fresh scan finds a credential or confidential value.
- A required change would alter the master document, an accepted ADR, a frozen
  preregistration section, or a trust-boundary schema.

## Definition of done
All repository-local criteria pass in a clean worktree, every allowed change is
in one signed-off commit series on one launch branch and one pull request, the
task records validation evidence, and the task remains
`blocked-human-review` until the documented privacy, legal, settings,
publication, and deployment gates are completed by the owner.
