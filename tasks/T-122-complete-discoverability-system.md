# T-122: Complete the public discoverability and measurement system

---
id: T-122
status: done
depends_on: [T-121]
invariant: "master doc §8–§9 and §12; preserve scientific honesty, privacy, capability-bounded claims, accessibility, and human-only external gates"
---

## Objective
Make Irrevon's public repository and generated website truthfully discoverable, citable,
measurable, and ready for owner-controlled search-engine and analytics setup.

## Why
The public research-preview launch needs a coherent search, answer-engine, crawler,
attribution, and measurement layer. The implementation must follow current primary-source
guidance without inventing authority, results, adoption, or guarantees, and without
performing external account, deployment, or repository-setting mutations.

## Context — read these first
- `AGENTS.md`
- `README.md`
- `docs/master-doc.md` §§6–§9, §12, and §13
- `docs/security-policy.md`
- `docs/benchmark.md`
- `docs/ci.md`
- `site/README.md`
- `site/src/`

## Scope
**Allowed to write:** this task file; `README.md`; public community and citation metadata;
`docs/`; `scripts/`; `tests/`; `site/`; `.github/workflows/`; `Makefile`; generated public
documentation mirrors; and machine-readable discoverability, metric, crawler, campaign, or
verification configuration required by the objective.

**Forbidden:** `docs/master-doc.md`; rewriting accepted ADR decision text; deleting or
resolving review-queue entries; editing frozen preregistration sections; credentials or
verification tokens; external account creation; webmaster verification; sitemap or
IndexNow submission; analytics/provider mutation; repository setting/topic/description
mutation; deployment; publication; tag/release creation; history rewrite; invented claims,
contacts, entities, users, customers, results, ratings, or authority.

## Acceptance criteria
- [x] Every canonical indexable page has a unique intent-aligned title, description, H1,
      canonical, crawlable internal path, and truthful visible answer-first content.
- [x] Robots, sitemap, crawler policy, verification hooks, IndexNow filtering, structured
      data, social/video metadata, and noindex boundaries are explicit and tested against
      generated HTML.
- [x] Privacy-safe analytics events and lowercase campaign attribution are allowlisted,
      reject sensitive/high-cardinality data, and degrade safely when provider support is
      unavailable.
- [x] Owner setup and a machine-readable metric catalog cover webmaster tools, analytics,
      referral attribution, GitHub traffic retention, and post-deployment indexing without
      making external changes.
- [x] GitHub-facing metadata and README discovery language remain concise, natural, and
      scientifically honest.
- [x] Failure tests reject duplicate metadata, noncanonical or unsafe IndexNow URLs,
      crawler-policy drift, invalid campaigns, sensitive analytics fields, thin pages,
      suspicious repetition, broken links/fragments, and invalid structured data.
- [x] Built-site inspection, accessibility, responsive, performance, site, and repository
      validation gates pass in both local and Linux browser environments.

## Required validation
```text
make check
make site-check
make site-build
make site-test
make site-vrt
make launch-audit
git diff --check
```

## Documentation updates
Document crawler/training policy, webmaster verification and submission, IndexNow,
privacy-safe analytics and campaigns, metric definitions, GitHub owner settings, and the
limits of optional aids such as `llms.txt`.

## Human review triggers — stop and ask if:
- Work requires an external account, verification, submission, deployment, publication,
  provider/repository setting mutation, or secret.
- Search positioning would require a claim beyond current implementation or evidence.
- A requested metric cannot be collected without personal or sensitive data.

## Definition of done
All criteria are checked; generated HTML and owner-operated tooling are tested; validation
evidence is recorded; no forbidden external action occurs; the task is marked done; and all
changes are committed and pushed to the existing launch pull request.

## Validation evidence

- `make check`, `make site-check`, `make site-build`, `make site-test`, `make site-vrt`,
  and `git diff --check`: exit 0. The generated site contains 69 pages; the browser suite
  passed 384 checks and the desktop/tablet/mobile, light/dark, and reduced-motion visual
  matrix passed 418 captures.
- `COMPOSE_PROJECT_NAME=irrevon make launch-audit`: exit 0 in one uninterrupted rerun.
  It passed 457 non-integration tests, 256 PostgreSQL integration tests, 92 Workbench unit
  tests, 80 Storybook tests, 133 Workbench browser/accessibility tests, five real-engine
  browser tests, all marketing-site checks and captures, 12 benchmark smoke combinations,
  clean wheel/sdist journeys, SPDX/checksum/license verification, public-data inspection,
  and source/built-artifact secret scans.
- A separate ephemeral `node:24-bookworm` Linux container built the production site and
  passed all 384 Chromium checks, including the 320px responsive regression. The container
  received the canonical repository/origin, reviewed commit SHA, and pinned master-document
  hash as validation-only inputs.
- Campaign tooling tests, IndexNow tooling tests, and crawler-policy tests passed (68 Python
  script tests and six Node policy tests). IndexNow dry-run accepted all 67 canonical live
  URLs with zero deleted URLs and made no network request.
- A preview-mode build emitted `noindex,nofollow` on all 69 HTML pages and a disallow-all
  robots policy; the production build was restored afterward.
- No webmaster verification, sitemap/IndexNow submission, analytics/provider mutation,
  repository setting change, deployment, video publication, package publication, release,
  tag, signing, or upload occurred.
