---
title: "CI — how this repository builds"
description: "The CI workflow map: tiers, required checks, owner settings checklist, and local parity via make targets."
sourcePath: "docs/ci.md"
sourceSha256: "d0bb93abaaca844159bca91abd4f7758cfecf99d19db86931399c7061833b71d"
syncedAt: "2026-07-22"
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
| [`nightly.yml`](../.github/workflows/nightly.yml) | cron 09:17 UTC + dispatch | Full local gate on a clean machine + online audits (external links, networked zizmor); grows the T3 suites at M3+; files/updates one dedup'd `nightly-failure` issue on red | active |
| [`sandbox.yml`](../.github/workflows/sandbox.yml) | `workflow_dispatch` only | T4 credentialed sandbox contract tests — skeleton, activates at M4; gated by the `sandbox` environment | skeleton |
| [`benchmark.yml`](../.github/workflows/benchmark.yml) | `workflow_dispatch` only | IrrevonBench preregistered runs — skeleton, activates at M7; gated by the `benchmark` environment | skeleton |
| [`release.yml`](../.github/workflows/release.yml) | disabled (`if: false` guard) | Prepared release pipeline (version check, deterministic build, checksums, SBOM, attestation, human approval, OIDC publish) — enabled only at the public-release gate | disabled |
| [`dependabot.yml`](../.github/dependabot.yml) | monthly | Noise-contained policy (tuned at consolidation, 2026-07-21): one grouped catch-all PR per ecosystem (actions / uv / npm), `open-pull-requests-limit: 1`, 7-day cooldowns (30-day uv majors; npm majors ignored — deliberate human migrations per ADR-0016), owner auto-assigned; security PRs bypass schedule and cooldown | active |

## Tier table — what runs when

| Tier | Job (workflow) | Condition | Runs | Today |
|---|---|---|---|---|
| T0 docs/static | `docs` (ci) | always, every push/PR | `make check` (links, schemas, secrets, integrity, actionslint, frozen, assets, third-party, bench-integrity) | active |
| T0 backend static | `py-check` (ci) | backend paths changed AND `pyproject.toml` exists | `make py-check` | active (engine landed; skips cleanly on docs-only PRs) |
| T1 backend unit+property | `py-test` (ci) | same | `make py-test` (≥1,000 Hypothesis cases/invariant — spec, never lowered) | active (same skip rule) |
| F0 web static | `web-check` (ci) | `web/` paths changed AND `web/` exists | `make web-check` | active (workbench landed; skips cleanly on non-web PRs) |
| F1/F2 web tests | `web-test` (ci) | same | `make web-test` | active (same skip rule) |
| workflow security | `workflow-security` (ci) | `.github/workflows/**` changed | actionlint + zizmor (online, pedantic) | active |
| T2 integration | `py-test-integration` (ci) | backend changes | `make py-test-integration` vs the digest-pinned compose Postgres | active (wired at the rebuild consolidation, per this row's earlier "due" note) |
| site static | `site-check` (ci) | `site/` changed | `make site-check` (astro check + every drift gate) | active (wired at the rebuild consolidation) |
| site tests | `site-test` (ci) | `site/` changed | `make site-test` (build + Playwright a11y/keyboard/no-JS/links/budgets/search/anti-fabrication/SEO) | active |
| live E2E | `web-e2e-live` (ci) | backend OR `web/` changed (both slices must exist) | `make web-e2e-live` (real demo → real `irrevon serve` → Playwright against the staged packaged workbench) | active |
| — | `ci-required` (ci) | `if: always()` | aggregates all of the above; the ONLY required check | active |
| T3 nightly | `validate` + `t3-backend` (nightly) | cron | `make check` + online audits; conformance-budget properties + full integration suite (fault-matrix subset vs the stub destination) | active |
| wheel smoke | `wheel-smoke` (nightly) | cron | `make dist-smoke` (= `make dist` + the Node-less container smoke; ADR-0018 chain, wheel + sdist legs) | active — nightly, not PR: needs docker + a second full web build + wheel build; the PR-side integration truth is `web-e2e-live` |
| T4 sandbox | `sandbox-contract` (sandbox) | human dispatch + env approval | M4: `make sandbox-contract` | skeleton |
| benchmark | `bench` (benchmark) | human dispatch + env approval | M7: preregistered suites, cache-free, sanitized evidence (`irrevon bench run` — integrity refusal until the human Stage-B freeze) | skeleton |

The bench foundation (ADR-0030, proposed) additionally added: `bench-integrity`
into `make check` (stdlib-only fixture/canary/holdout/freeze gate) and
`bench-smoke` into `make check-all` (CLI end-to-end over two dev workloads,
conventional arms, no database). The full harness suites run inside the
existing `py-test` / `py-test-integration` tiers (`tests/bench/`).

A docs-only PR runs `changes` + `docs` (+ `workflow-security` if workflows changed) and
passes legitimately — conditional jobs skip and the aggregator verifies each skip against
the change detection.

## Local parity

**Every CI job body runs exactly one `make` target** after the pinned tool bootstrap
([`scripts/bootstrap-tools.sh`](../scripts/bootstrap-tools.sh) — the single
checksum-verified pin table shared by `make tools-pinned`, CI, and cloud agents). What CI
checks is what `make check` checks. `[DD]` Three documented exceptions: `workflow-security`
runs zizmor with network advisories and nightly runs lychee/zizmor online (*online variants*
of offline make gates — the local gate stays deterministic `--offline` on purpose), and
`dependency-review` (GitHub-owned action, SHA-pinned, `contents: read`) has no local
equivalent because it consumes GitHub's advisory database against the PR diff; it is
deliberately OUTSIDE the `ci-required` aggregator (it exists only on pull_request events —
the pending-forever trap).

## Owner settings checklist (HUMAN-only; agents are hook-blocked from all of it)

**Script:** [`scripts/setup-repo-settings.sh`](../scripts/setup-repo-settings.sh) automates
items 1–5 below (`bash scripts/setup-repo-settings.sh`, idempotent, read-back verification
included) and item 6 (`--phase2`, self-guarded: refuses until `ci-required` has reported
green on a real PR). The Actions allowlist/SHA-pin checkbox in item 3 and items 7–8 stay
manual UI steps.

Now (with this branch's merge):

1. **Secret scanning + push protection** — Settings → Advanced Security → enable
   *Secret scanning*, *Push protection*, and *Scan for non-provider patterns*.
   Automated by `scripts/setup-repo-settings.sh` (phase 1).
   Second layer only — local gitleaks (pre-commit + `make secrets`) stays primary.
2. **Dependabot alerts + security updates** — same pane; automated by
   `scripts/setup-repo-settings.sh` (phase 1).
3. **Actions posture** — Settings → Actions → General: *Allow `<owner>`, and select
   non-`<owner>`, actions* with allowlist `astral-sh/setup-uv@*` (github-owned actions
   allowed; extend with `anchore/*`, `sigstore/*`, `pypa/*` only at the release gate);
   check **Require actions to be pinned to a full-length commit SHA**; fork-PR approval =
   **Require approval for all external contributors** (the default first-time-only tier is
   gameable `[VF]`); workflow permissions read-only, "create and approve pull requests" off.
4. **Ruleset phase 1** — Settings → Rules → Rulesets → New branch ruleset on the default
   branch: `deletion`, `non_fast_forward`, `pull_request` (0 required approvals — a solo
   owner cannot approve their own PR), `bypass_actors: []`.
5. **Create the `nightly-failure` label** (used by the nightly dedup job).

After `ci-required` has reported on at least one PR (order matters — see traps below):

6. **Ruleset phase 2** — add `required_status_checks` with the single context
   `ci-required`. Never list individual jobs.
7. **CodeQL default setup** — Settings → Advanced Security → CodeQL → Default. Idle (no
   supported language yet) but free and safe to enable `[VF]`.
8. Retention stays 90 days (public max). **Private vulnerability reporting**: verified
   enabled (API read, 2026-07-21) — see [SECURITY.md](../SECURITY.md).

Site deploys (not a workflow):

9. **The site deploys to Vercel, not from CI** ([ADR-0027](decisions/0027-site-vercel-deploy.md);
   the former dispatch-only `site-deploy.yml` Pages workflow is deleted). A deploy is an
   owner-directed act: build `site/dist` with the deploy-provided `SITE_ORIGIN` /
   `SITE_REPO_URL` (`astro.config.mjs` embeds both at build time) and upload the static
   output; response headers come from `site/vercel.json`. Details in
   [site/README.md](../site/README.md). The repo-root `vercel.json` sets
   `git.deploymentEnabled: false` so the Vercel GitHub integration never deploys on push
   (push-triggered deploys are policy-forbidden, and the git-connected project's
   auto-deploys were failing on every push as a red `Vercel` commit status).

Before the first M4/M7 dispatch:

10. **Environments** — Settings → Environments → create `sandbox` and `benchmark`, each
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
  evaluates to `""`. Sandbox/benchmark jobs carry explicit non-empty guards before any
  credentialed step — keep that pattern for every future secret.
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

## Design notes — cuts from the source designs `[DD]`

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
- **Cut Postgres service containers from committed YAML**: no code exists; the digest pin
  would rot unused. The T2/T3 bodies are documented (here and in workflow comments) and
  land with the code at M3.
- **Cut the GitHub Pro pairing recommendation** (CI design review): rulesets/environments are free on
  public repos; Pro buys nothing while public.
- **Deferred: PR template** — the owner is the sole author today; a checklist nobody else
  reads is ceremony. Adopt at code landing or first external contributor (whichever first).
- **Deferred: CODEOWNERS, auto-labeling, Scorecard, README badges** — per the CI design
  review rulings (solo repo; Scorecard needs a scoped `security-events: write` exception
  that deserves its own decision at M3).
- **Deferred: Cursor CLI diagnostic workflow** (CI design review): its guardrails are designed, but
  it requires a `CURSOR_API_KEY` secret — which violates the no-repo-level-secrets rule
  until an owner-created environment holds it — and the vendor installer has no published
  stable checksum to pin. Revisit when both close.
- **`nightly-failure` template placement**: lives in `.github/ISSUE_TEMPLATE/` with
  frontmatter so the same file serves manual filing; the workflow strips frontmatter and
  fills placeholders from trusted context only.
