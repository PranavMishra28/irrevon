---
title: "CI — how this repository builds"
description: "The CI workflow map: tiers, required checks, owner settings checklist, and local parity via make targets."
sourcePath: "docs/ci.md"
sourceSha256: "761404ebe54fc4b30c585d5523a1970a4badf05a6c63794a2dc453b4e7abb697"
syncedAt: "2026-07-24"
section: "Governance"
renderTitle: false
---

# CI — workflow map, tiers, owner checklist, troubleshooting

One page. Workflows live in [`.github/workflows/`](../.github/workflows/); every gate they
run is a [Makefile](../Makefile) target (see [Local parity](#local-parity)). Sources: the
CI design reviews ratified 2026-07-21 (internal working papers; the durable decisions are
this page + the workflows); platform semantics below are `[VF]` against GitHub docs as of
that date.

## Workflow map

| Workflow | Trigger | Purpose | State |
|---|---|---|---|
| [`ci.yml`](../.github/workflows/ci.yml) | every push + PR | The required PR gate: change detection → conditional jobs → the `ci-required` aggregator | active |
| [`nightly.yml`](../.github/workflows/nightly.yml) | cron 09:17 UTC + dispatch | Full local gate on a clean machine + online audits (external links, networked zizmor); grows the T3 suites at M3+; files/updates one title-deduplicated nightly-failure issue on red | active |
| [`sandbox.yml`](../.github/workflows/sandbox.yml) | `workflow_dispatch` only | T4 sandbox contracts — fail-closed skeleton, gated by the `sandbox` environment; every dispatch is deliberately red until human M4 activation | skeleton (always refuses) |
| [`benchmark.yml`](../.github/workflows/benchmark.yml) | `workflow_dispatch` only | IrrevonBench preregistered runs — fail-closed skeleton, gated by the `benchmark` environment; every dispatch is deliberately red until human Stage-B activation | skeleton (always refuses) |
| [`release.yml`](../.github/workflows/release.yml) | PR + manual dry run; canonical `vMAJOR.MINOR.PATCH` tag | Non-publishing artifact dry run on PRs; clean tagged build, exact HEAD/tag/current-main identity, Node-24/content/renderer-hash/smoke gates, checksums, lock-aware SPDX SBOM, artifact attestation, then protected-environment PyPI/GitHub publication | prepared; no release exists |
| [`scorecard.yml`](../.github/workflows/scorecard.yml) | main/protection change + weekly | OpenSSF Scorecard evidence and SARIF upload | active |
| [`dependabot.yml`](../.github/dependabot.yml) | monthly routine + prompt security | One multi-ecosystem routine PR across Actions, uv, web npm, site npm, and Docker; security remediation remains grouped per ecosystem | active |

## Tier table — what runs when

| Tier | Job (workflow) | Condition | Runs | Today |
|---|---|---|---|---|
| T0 docs/static | `docs` (ci) | always, every push/PR | `make check` (links, schemas, secrets, integrity, actionslint, frozen, assets, third-party, bench-integrity) | active |
| T0 backend static | `py-check` (ci) | backend paths changed AND `pyproject.toml` exists | `make py-check` | active (engine landed; skips cleanly on docs-only PRs) |
| T1 backend unit+property | `py-test` (ci) | same | `make py-test` (≥1,000 Hypothesis cases/invariant — spec, never lowered) | active (same skip rule) |
| F0 web static | `web-check` (ci) | `web/` paths changed AND `web/` exists | `make web-check` | active (workbench landed; skips cleanly on non-web PRs) |
| F1/F2 web tests | `web-test` (ci) | same | `make web-test` | active (same skip rule) |
| F3 web browser + accessibility | `web-e2e` (ci) | same | `make web-e2e` (built review app; full workflow matrix + route-wide axe in both themes, zero retries) | active (same skip rule; required through `ci-required`) |
| workflow security | `workflow-security` (ci) | `.github/workflows/**` changed | actionlint + zizmor (online, pedantic) | active |
| T2 integration | `py-test-integration` (ci) | backend changes | `make py-test-integration` vs the digest-pinned compose Postgres | active (wired at the rebuild consolidation, per this row's earlier "due" note) |
| site static | `site-check` (ci) | `site/` changed | `make site-check` (astro check + every drift gate) | active (wired at the rebuild consolidation) |
| site tests | `site-test` (ci) | `site/` changed | `make site-test` (build + Playwright a11y/keyboard/no-JS/links/budgets/search/anti-fabrication/SEO) | active |
| live E2E | `web-e2e-live` (ci) | backend OR `web/` changed (both slices must exist) | `make web-e2e-live` (real demo → real `irrevon serve` → Playwright against the staged packaged workbench) | active |
| — | `ci-required` (ci) | `if: always()` | aggregates all of the above; the ONLY required check | active |
| T3 nightly | `validate` + `t3-backend` (nightly) | cron | `make check` + online audits; conformance-budget properties + full integration suite (fault-matrix subset vs the stub destination) | active |
| wheel smoke | `wheel-smoke` (nightly) | cron | `make dist-smoke` (= `make dist` + the Node-less container smoke; ADR-0018 chain, wheel + sdist legs) | active — nightly, not PR: needs docker + a second full web build + wheel build; the PR-side integration truth is `web-e2e-live` |
| T4 sandbox | `sandbox-contract` (sandbox) | human dispatch + env approval | Today: exactly `make sandbox-stage-m4`, whose reserved recipe unconditionally refuses. M4 activation must replace it with the reviewed credentialed contract recipe | skeleton (always refuses) |
| benchmark | `bench` (benchmark) | human dispatch + env approval | Today: exactly `make benchmark-stage-b`, whose reserved recipe unconditionally refuses. M7 activation must replace it with the complete preregistered, cache-free, sanitized-evidence recipe | skeleton (always refuses) |
| package release | `dry-run` / `validate-build` / `build-attest` / publish jobs (release) | PR/manual is non-publishing; canonical version tag only for publication | locked Python validators + `make launch-audit` + Node-24 release dry run; privileged attestation/publish jobs download validated artifacts and never execute repository code | prepared; protected `release` environment and publisher binding are owner gates |

The local `make check-all` ladder includes `web-check`, `web-test`, and `web-e2e`; F4
pixel baselines remain the explicit container-only `make web-vrt` gate. The bench
foundation (ADR-0030, proposed) additionally added: `bench-integrity`
into `make check` (stdlib-only fixture/canary/holdout/freeze gate) and
`bench-smoke` into `make check-all` (CLI end-to-end over two dev workloads,
conventional arms, no database). The full harness suites run inside the
existing `py-test` / `py-test-integration` tiers (`tests/bench/`).

A docs-only PR runs `changes` + `docs` (+ `workflow-security` if workflows changed) and
passes legitimately — conditional jobs skip and the aggregator verifies each skip against
the change detection.

### Node runtime contract

`[DD]` Active jobs never inherit the mutable Node version preinstalled on
`ubuntu-latest`. Every job that invokes Corepack first runs the full-SHA-pinned
`actions/setup-node` v7.0.0 action and resolves Node from the package it operates:
`web/.nvmrc` for workbench/build jobs and `site/.nvmrc` for marketing-site jobs. Package
manager versions remain locked by each package's `packageManager` field and lockfile.
A stdlib-only workflow contract test fails if any active Corepack job loses, reorders, or
changes that runtime setup.

### Fail-closed sandbox skeleton

`[DD]` The `sandbox` workflow cannot be used as live-provider evidence today. Its sole
executable body after checkout is the reserved `make sandbox-stage-m4` entrypoint, and that
target unconditionally exits nonzero without reading an input or credential, testing for a
file, invoking a harness, creating an artifact, or contacting a provider. Consequently,
configuring repository state cannot turn the dormant skeleton green.

Activation is a separate human-reviewed M4 task after Stage A, the human ADR-0010 and
ADR-0012 decisions, applicable terms review, and a real credentialed contract recipe. In one
reviewed change it must replace the refusal with that recipe, add guards for the
human-selected environment credentials, preserve manual dispatch and environment approval,
and replace the static refusal contract with tests of the active target. A green
pre-activation dispatch is a workflow-integrity failure, not a successful sandbox contract.

### Fail-closed benchmark skeleton

`[DD]` The `benchmark` workflow cannot be used as evidence today. Its sole executable body
after checkout is the reserved `make benchmark-stage-b` entrypoint, and that target
unconditionally exits nonzero without reading a secret, testing for a file, invoking the
harness, or contacting a provider. Consequently, creating the `benchmark` environment,
configuring any secret, or committing a registration-shaped file cannot turn the skeleton
green.

Activation is a separate human-approved Stage-B task after the preregistration's P7 gate. In
one reviewed change it must replace the refusal with the complete registered run procedure,
pin its environment/tooling, add credential guards before any credentialed step, preserve
the manual trigger and environment approval, and replace the static refusal contract with
tests of the real target. A green pre-activation dispatch is a workflow integrity failure,
not a successful benchmark.

### Prepared package release

`[DD]` Pull requests and manual dispatches can only run the non-publishing dry
run. Publication requires a canonical-repository tag that exactly matches a
non-development package version and whose peeled commit exactly equals current
`origin/main` and checked-out `HEAD`; merely being an ancestor of main is
insufficient. Repository code runs only in an unprivileged validation job; a
separate job downloads those artifacts to request GitHub attestations. The
candidate build refuses non-Node-24 Workbench builds. Twine 6.2.0,
`check-jsonschema`, PyPA `pip-audit` 2.10.1, and SPDX Tools are
exact-constrained in the dedicated `release-validation` group and transitively
resolved by `uv.lock`; release jobs invoke the group through `uv run --locked`.
The audit consumes a hash-bearing frozen export of only the production graph
without dependency resolution. Twine's `check --strict` PyPI
long-description gate must leave the wheel/sdist hashes unchanged, after which
the archive manifests are checked again. PyPI and GitHub publication are
separate least-privilege jobs behind the owner-created and protected `release`
environment. No long-lived publishing token is accepted. The workflow is
prepared but has never produced a release or attestation; setup and execution
remain the owner actions in
[release-process.md](release-process.md).

### Dependabot update policy

`[DD]` Routine version updates use GitHub's `multi-ecosystem-groups` contract:
all five supported dependency trees join `monthly-routine`, so the scheduled
steady state is at most one open routine pull request. Every entry retains a
seven-day cooldown and a one-PR version-update limit. The group and each
ecosystem assign the owner and the explicit `dependencies` label; no automatic
merge path exists.

Security fixes are intentionally different. GitHub does not combine security
updates across package ecosystems, so each ecosystem has its own
`applies-to: security-updates` catch-all group. Security updates bypass routine
schedules and cooldowns and keep their separate platform limit. Repository-level
**Grouped security updates** must remain enabled so qualifying fixes across
directories within an ecosystem consolidate without suppressing remediation.

#### Quarterly major-upgrade review

Routine major updates are disabled for `/web` and `/site`, whose dependencies
are exact-pinned and validated as complete stacks. Once per quarter, the owner:

1. reviews upstream release notes and security advisories for deferred majors;
2. opens one normal, non-Dependabot change for one stack at a time;
3. regenerates only that stack's lockfile and dependency notices;
4. runs its static, unit, browser, accessibility, visual, and package embedding
   gates plus `make check`; and
5. merges only through the ordinary `ci-required` path, with rollback notes for
   material runtime or build changes.

Urgent security remediation never waits for this quarterly cycle.

## Local parity

Required CI gate bodies run their documented `make` target after
[`scripts/bootstrap-tools.sh`](../scripts/bootstrap-tools.sh). Its native
lychee/gitleaks/actionlint/zizmor archives are checksum-verified. The generic
docs/nightly path retains the explicitly version-pinned `check-jsonschema`
fallback for runners without uv; the release workflow does not use that
fallback and instead resolves both Python validators from `uv.lock` through
`uv run --locked`. What CI checks is what the corresponding local Make target
checks. `[DD]` Three non-Make exceptions remain: `workflow-security` runs zizmor
with network advisories and nightly runs lychee/zizmor online (*online variants*
of offline make gates — the local gate stays deterministic `--offline` on
purpose), and `dependency-review` (GitHub-owned action, SHA-pinned,
`contents: read`) has no local equivalent because it consumes GitHub's advisory
database against the PR diff. The job exists only on `pull_request` events, is
included in `ci-required.needs`, and the aggregator requires it to succeed on
pull requests while accepting its skip on push events.

## Owner settings checklist (HUMAN-only; agents are hook-blocked from all of it)

**Script:** [`scripts/setup-repo-settings.sh`](../scripts/setup-repo-settings.sh) automates
secret scanning, Dependabot, default workflow permissions, fork approval, and the initial
ruleset (`bash scripts/setup-repo-settings.sh`, idempotent, semantic read-back included).
Its `--phase2` mode is self-guarded and refuses until `ci-required` has reported green on a
real PR. The Actions allowlist/SHA-pin checkbox, CodeQL default setup, and private
vulnerability reporting remain manual UI/read-back controls.

Now (with this branch's merge):

1. **Secret scanning + push protection** — Settings → Advanced Security → enable
   *Secret scanning*, *Push protection*, and *Scan for non-provider patterns*.
   Automated by `scripts/setup-repo-settings.sh` (phase 1).
   Second layer only — local gitleaks (pre-commit + `make secrets`) stays primary.
2. **Dependabot alerts + security updates** — same pane; automated by
   `scripts/setup-repo-settings.sh` (phase 1). Also enable **Grouped security
   updates**; configuration groups remain per ecosystem because GitHub does not
   combine security fixes across ecosystems.
3. **Actions posture** — Settings → Actions → General: *Allow `<owner>`, and select
   non-`<owner>`, actions* with allowlist `astral-sh/setup-uv@*`,
   `ossf/scorecard-action@*`, and `pypa/gh-action-pypi-publish@*` (GitHub-owned
   `actions/*` and `github/*` actions are allowed);
   check **Require actions to be pinned to a full-length commit SHA**; fork-PR approval =
   **Require approval for all external contributors** (the default first-time-only tier is
   gameable `[VF]`); workflow permissions read-only, "create and approve pull requests" off.
   **Read-back 2026-07-24:** the repository still allows all actions and has platform
   SHA-pin enforcement disabled. This remains an owner launch action; repository
   workflows are individually full-SHA-pinned and locally checked meanwhile.
4. **Ruleset phase 1** — Settings → Rules → Rulesets → New branch ruleset on the default
   branch: `deletion`, `non_fast_forward`, `pull_request` (0 required approvals — a solo
   owner cannot approve their own PR), `bypass_actors: []`.
   **Read-back 2026-07-24:** the active ruleset has `ci-required`, but also has an
   always-allowed repository-role bypass actor. Remove that bypass before launch. The
   setup script now refuses semantic drift instead of treating a same-named ruleset as
   correct.
After `ci-required` has reported on at least one PR (order matters — see traps below):

5. **Ruleset phase 2** — add `required_status_checks` with the single context
   `ci-required`. Never list individual jobs.
6. **CodeQL default setup** — Settings → Advanced Security → CodeQL → Default. Verified
   active for Python and JavaScript/TypeScript on 2026-07-24. Keep the settings-managed
   scanner enabled; GitHub rejects a competing advanced-configuration workflow while
   default setup is active `[VF]`.
7. Retention stays 90 days (public max). **Private vulnerability reporting**: verified
   enabled (API read, 2026-07-21) — see [SECURITY.md](../SECURITY.md).
   **Additional read-back 2026-07-24:** Discussions and non-provider secret
   scanning are disabled; immutable releases are disabled; and the `release`,
   `sandbox`, and `benchmark` environments are absent. Before exposing any
   Discussion link, the owner must enable Discussions; create or verify
   `Announcements`, `Q&A`, `Ideas and feedback`, and `Show and tell`; publish
   and pin a welcome post; and read back every category URL. Create and protect
   each workflow environment before its first use; never rely on GitHub's
   silent auto-creation behavior.

Site deploys (not a GitHub Actions workflow):

8. **Repository policy permits Vercel auto-deployment from `main` only**
   ([ADR-0038](decisions/0038-main-vercel-auto-deploy.md), superseding
   ADR-0027's manual-upload mechanic). The root
   [`vercel.json`](../vercel.json) overrides the
   project's stale Python autodetection, installs the locked `site/` pnpm
   graph, invokes `scripts/vercel-build.sh`, serves `site/dist`, and carries
   the response-header contract. Its branch map disables every automatic
   deployment except `main`; the wrapper independently refuses a non-production
   environment, non-`main` ref, or non-full commit SHA. Root `vercel.json`
   changes select the complete site CI slice. This path deploys only the
   marketing/docs site—it cannot merge code or publish Python packages,
   GitHub Releases, benchmarks, or provider activity. Details in
   [site/README.md](../site/README.md).
   Vercel does not wait for `ci-required`; the normal pull-request path supplies
   that review boundary, while the repository-role bypass reported in item 4
   must be removed before launch. The linked Vercel project was paused on
   2026-07-24, and the authenticated read-back did not expose its Production
   Branch. After merging, the owner must confirm Production Branch = `main`,
   reactivate the project, and then compare live `/version.json` with the
   intended commit.
   **Production read-back 2026-07-24:** the public alias serves content matching
   the July 22 pre-main build and `/version.json` is absent. This content
   comparison is not cryptographic proof of a deployed commit. Treat the alias
   as stale until the reviewed auto-deployment reaches `main` and the owner
   verifies its version document and intended commit.

Before the first M4/M7 dispatch:

9. **Environments** — Settings → Environments → create `sandbox` and `benchmark`, each
   with *Required reviewers* = owner, *Prevent self-review* UNCHECKED (checking it
   deadlocks a solo owner), deployment branches = `main` only; put sandbox-only secrets
   there — **no repo-level secrets, ever** `[DD]`. Create the environments BEFORE any
   dispatch: a run referencing a missing environment silently auto-creates it unprotected.
   Caveat `[VF]`: converting the repo back to private silently drops environment
   protection and secrets — re-privatization must re-trigger this checklist.

## Troubleshooting

- **Skipped counts as passing.** A required status check whose job was skipped satisfies
  the ruleset `[VF]`. That is why individual jobs are never required and `ci-required`
  fails on skips that contradict change detection. If a code PR shows green with skipped
  code jobs, the change filter is broken — fix `changes` in ci.yml, never the aggregator.
- **Never-reported stays pending.** A required check that never reports blocks the PR
  forever `[VF]`. So: no workflow-level `paths:` filters on ci.yml, and never add the
  ruleset requirement before the workflow has reported once on a real PR.
- **Adversarial-filter residual.** A PR can edit the change filter *and* code in one diff;
  the aggregator then sees "legit" skips. The aggregator defends against accidental skips;
  human review of any workflow diff is the control against adversarial ones `[EI]`.
- **Missing secret = empty string.** An absent Actions secret does not fail a job; it
  evaluates to `""`. The fail-closed sandbox/benchmark skeletons deliberately read no
  secret today. Their activation changes must add an explicit non-empty guard before each
  credentialed step; keep that pattern for every future secret.
- **Nightly silently auto-disables** after 60 days without repo activity (public repos)
  `[VF]`. Quarterly sweep: confirm the nightly workflow is still enabled, re-verify the
  action pin table and (at M3+) the Postgres digest, which Dependabot does not bump.
- **Docs gate fails on a ratification PR.** The frozen gate
  ([`scripts/check-frozen.sh`](../scripts/check-frozen.sh)) treats
  `docs/review-queue.md` as append-only, with ONE exception — a human ratification
  integration: deletions pass only when the same PR range carries the master-doc
  re-pin (`docs/master-doc.md` + `scripts/master-doc.sha256` changed together, the
  human-only amendment act) AND the queue's added lines record the ratifying
  amendment (`AM-<n>` … `RATIFIED`). Deletions without both pieces of evidence
  still fail — never exempt the file or skip the gate on PRs. The scenario matrix
  lives in `tests/scripts/test_check_frozen.py`.
- **Push protection blocks a push:** rotate/remove the secret and recommit — never bypass
  (hook- and policy-blocked).
- **Nightly external-link failures** are often flakes: follow the triage protocol in the
  auto-filed issue; close only after a green manual re-run.

## Design notes — historical cuts and current reconciliation `[DD]`

Reconciliation rule: the public-repo review findings supersede the earlier private-repo
design.

- **Cut `gitleaks/gitleaks-action` job** (from the earlier security.yml design): redundant
  with the `make secrets` parity scan already inside `make check`; the CI design review
  itself named the parity scan as the keeper if the redundancy chafed.
- **Cut `zizmor-action` and separate `security.yml`/`docs-check.yml` workflows**: replaced
  by the pinned zizmor/actionlint binaries from the one bootstrap pin table (offline in
  `make check`, online in `workflow-security`/nightly) and by the single always-running
  ci.yml — required-check semantics on a public repo make the aggregator pattern, not
  separate path-filtered workflows, the correct shape. Two fewer third-party actions.
- **Cut the workflow-level `on.paths` filters** (ci.yml): they break required checks
  (pending-forever trap); replaced by the `changes` job + aggregator.
- **Postgres service-container cut was temporary:** once the M3 engine and
  integration suite landed, the digest-pinned Compose service and active T2/T3
  jobs landed with them. The current workflow and tier tables above are
  authoritative.
- **Cut the GitHub Pro pairing recommendation** (CI design review): rulesets/environments are free on
  public repos; Pro buys nothing while public.
- **Community and ownership controls have landed:** the PR template,
  repository-wide CODEOWNERS baseline with path-specific rules, README badges,
  and Scorecard workflow are active. Nightly failure labeling is deliberately
  limited to the fixed owner-created label and title-deduplicated failure issue;
  there is no general comment-driven auto-labeling bot.
- **Deferred: Cursor CLI diagnostic workflow** (CI design review): its guardrails are designed, but
  it requires a `CURSOR_API_KEY` secret — which violates the no-repo-level-secrets rule
  until an owner-created environment holds it — and the vendor installer has no published
  stable checksum to pin. Revisit when both close.
- **Nightly link parity:** `make links-online` shares the offline gate's source exclusions
  and Vite public-directory remaps, then adds external requests. Exact bot-blocked primary
  sources may be excluded individually; broad 4xx acceptance is forbidden.
- **Wheel-smoke network:** Postgres remains host-loopback-only. The Node-less smoke
  container joins the compose network and reaches the `ledger-db-test` service by its
  internal DNS name, which works on Linux without widening the host port binding.
- **Nightly-failure body placement:** lives at
  `.github/nightly-failure-body.md`, outside the public issue chooser. The
  workflow fills placeholders from trusted context only and deduplicates by the
  fixed issue title.
