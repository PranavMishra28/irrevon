# T-121: Complete the public open-source launch

---
id: T-121
status: done
depends_on: [T-120]
invariant: "master doc §6–§9 and §12; preserve capability-bounded guarantees, evidence truth, benchmark integrity, and human-only irreversible gates"
---

## Objective
Make every reversible repository-local change required for a coherent public research-preview
launch, with a complete DCO-based contribution path, supported single-writer deployment
boundary, executable release dry run, launch audit, and public surfaces that match current code.

## Why
The owner has ratified Apache-2.0 inbound-equals-outbound contributions with DCO sign-off and
requested one launch-completion PR. The implementation is substantial, but public onboarding,
governance, packaging, deployment, observability, privacy verification, and launch gates must
be reconciled into one tested product posture without manufacturing production or scientific
evidence.

## Context — read these first
- `AGENTS.md`
- `README.md`
- `docs/master-doc.md` §§6–§9, §12, and §13
- `docs/decisions/README.md`
- `docs/review-queue.md`
- `docs/execution-plan.md`
- `docs/security-policy.md`
- `docs/benchmark.md`
- `docs/operations.md`
- `docs/ci.md`

## Scope
**Allowed to write:** this task file; all current repository files except the forbidden set
below; new public documentation, community-health files, tests, scripts, workflows, container
artifacts, generated site mirrors, schemas/examples, and proposed or owner-ratified ADRs
required by the launch directive.

**Forbidden:** `docs/master-doc.md`; rewriting accepted ADR decision text; deleting or
resolving `docs/review-queue.md` entries; editing frozen preregistration sections; credentials;
live provider calls; confirmatory experiments; preregistration freeze; package publication;
release/tag creation; deployment or Vercel mutation; repository visibility/settings changes;
history rewrite; external-account creation; spending; invented contacts, entities, customers,
results, certification, adoption, or production evidence.

## Acceptance criteria
- [x] Public truth, navigation, status, commands, generated documentation, and claims match
      the current implementation and clearly separate historical/governance records.
- [x] Apache-2.0 inbound-equals-outbound contributions with mandatory DCO sign-off and no CLA
      are coherently implemented and tested.
- [x] Package metadata and dry-run release automation are standards-complete, fail closed,
      produce checksums/SBOM/attestation-ready artifacts, and cannot publish during PR CI.
- [x] Current tree, packages, media, build contexts, reachable refs, and public history receive
      multi-method secret/PII/provenance review without committing sensitive findings.
- [x] Loopback evidence privacy, the evaluated single-writer boundary, observability, adapter
      boundaries, benchmark pre-freeze integrity, and comparison guidance are explicit and
      covered by regression tests.
- [x] README, site, and Workbench provide coherent stranger onboarding, contribution,
      operations, research-status, accessibility, responsive, and evidence-linked experiences.
- [x] `make launch-audit` produces human- and machine-readable fail-closed results.
- [x] The complete repository validation ladder passes from a clean tree.
- [x] Independent hostile review finds no remaining repository-local launch blocker.
- [x] One branch contains every change for one unmerged PR; nothing is deployed.

## Required validation
```text
make check
make check-all
make launch-audit
make py-check
make py-test
make py-test-integration
make web-check
make web-test
make web-e2e
make web-e2e-live
make site-check
make site-build
make site-test
make site-vrt
make dist-smoke
git diff --check
```

## Documentation updates
Reconcile public entry points, documentation hierarchy, roadmap/release status, governance,
security, compatibility, operations, release verification, site-generated mirrors, and
agent source-of-truth guidance.

## Completion evidence
- Twelve bounded review lanes covered governance/truth, privacy/supply chain, runtime/adapters,
  benchmark science, application security, UX/accessibility, clean-room packaging, prior art,
  SRE/deployment, documentation, hostile runtime review, and hostile supply-chain review.
- `make launch-audit` passed the repository, Python, PostgreSQL integration, Workbench,
  live-service, marketing-site, visual, benchmark, package, release-dry-run, public-data, and
  generated-artifact secret-scan stages without publishing.
- The test evidence includes 389 non-integration tests, 256 PostgreSQL integration tests,
  133 Workbench browser/accessibility tests, 5 real live-service browser tests, 364 marketing
  site checks, and 400 responsive visual captures.
- Clean Python 3.13 container installs of both wheel and sdist passed without Node.js; the
  packaged CLI completed explicit migration, doctor, demo, serve, and worker journeys.
- The release dry run produced checked wheel/sdist contents, SHA-256 checksums, exact bundled
  third-party license texts, and a 38-package SPDX SBOM, with no upload, signing, tagging,
  release, or deployment action.
- Repository-local findings are resolved. Remaining provider clearance, preregistration,
  protected-environment, hosting, and public-history decisions are explicitly owner-gated.

## Human review triggers — stop and ask if:
- Work requires any forbidden external/irreversible action rather than preparation.
- A genuine public-history exposure requires owner-controlled rewriting or credential action.
- A proposed runtime or benchmark invariant lacks explicit owner ratification.

## Definition of done
All criteria are checked; repository-local findings are fixed; the full validation and hostile
review loops pass; no writes fall outside scope; the task is marked done; and every completed
change is committed, pushed, and described in one unmerged pull request.
