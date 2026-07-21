# CI — workflow map, tiers, owner checklist, troubleshooting

One page. Workflows live in [`.github/workflows/`](../.github/workflows/); every gate they
run is a [Makefile](../Makefile) target (see [Local parity](#local-parity)). Sources: the
CI research tracks ratified 2026-07-21 (W7, CI-R1..R3, `.scratch/rc/` — local-only);
platform semantics below are `[VF]` against GitHub docs as of that date.

## Workflow map

| Workflow | Trigger | Purpose | State |
|---|---|---|---|
| [`ci.yml`](../.github/workflows/ci.yml) | every push + PR | The required PR gate: change detection → conditional jobs → the `ci-required` aggregator | active |
| [`nightly.yml`](../.github/workflows/nightly.yml) | cron 09:17 UTC + dispatch | Full local gate on a clean machine + online audits (external links, networked zizmor); grows the T3 suites at M3+; files/updates one dedup'd `nightly-failure` issue on red | active |
| [`sandbox.yml`](../.github/workflows/sandbox.yml) | `workflow_dispatch` only | T4 credentialed sandbox contract tests — skeleton, activates at M4; gated by the `sandbox` environment | skeleton |
| [`benchmark.yml`](../.github/workflows/benchmark.yml) | `workflow_dispatch` only | DetentBench preregistered runs — skeleton, activates at M7; gated by the `benchmark` environment | skeleton |
| [`release.yml`](../.github/workflows/release.yml) | disabled (`if: false` guard) | Prepared release pipeline (version check, deterministic build, checksums, SBOM, attestation, human approval, OIDC publish) — enabled only at the public-release gate | disabled |
| [`dependabot.yml`](../.github/dependabot.yml) | weekly | Action SHA-pin freshness (7-day cooldown) + uv and web/npm dependency updates (5-day cooldown, 30-day major cooldown), grouped | active |

## Tier table — what runs when

| Tier | Job (workflow) | Condition | Runs | Today |
|---|---|---|---|---|
| T0 docs/static | `docs` (ci) | always, every push/PR | `make check` (links, schemas, secrets, integrity, actionslint, frozen) | active |
| T0 backend static | `py-check` (ci) | backend paths changed AND `pyproject.toml` exists | `make py-check` | active (engine landed; skips cleanly on docs-only PRs) |
| T1 backend unit+property | `py-test` (ci) | same | `make py-test` (≥1,000 Hypothesis cases/invariant — spec, never lowered) | active (same skip rule) |
| F0 web static | `web-check` (ci) | `web/` paths changed AND `web/` exists | `make web-check` | active (workbench landed; skips cleanly on non-web PRs) |
| F1/F2 web tests | `web-test` (ci) | same | `make web-test` | active (same skip rule) |
| workflow security | `workflow-security` (ci) | `.github/workflows/**` changed | actionlint + zizmor (online, pedantic) | active |
| — | `ci-required` (ci) | `if: always()` | aggregates all of the above; the ONLY required check | active |
| T2 integration | *(added to ci.yml at M3)* | backend changes | `make py-test-integration` vs digest-pinned Postgres service container | **due**: the M3 engine + integration suite landed at consolidation; wire the service-container job in the next CI change |
| T3 nightly | `validate` (nightly) | cron | today: `make check` + online audits; M3+: big-budget properties, fault-matrix subset vs stub destination | active |
| T4 sandbox | `sandbox-contract` (sandbox) | human dispatch + env approval | M4: `make sandbox-contract` | skeleton |
| benchmark | `bench` (benchmark) | human dispatch + env approval | M7: preregistered suites, cache-free, sanitized evidence | skeleton |

A docs-only PR runs `changes` + `docs` (+ `workflow-security` if workflows changed) and
passes legitimately — conditional jobs skip and the aggregator verifies each skip against
the change detection.

## Local parity

**Every CI job body runs exactly one `make` target** after the pinned tool bootstrap
([`scripts/bootstrap-tools.sh`](../scripts/bootstrap-tools.sh) — the single
checksum-verified pin table shared by `make tools-pinned`, CI, and cloud agents). What CI
checks is what `make check` checks. `[DD]` Two documented exceptions, both *online variants*
of offline make gates: `workflow-security` runs zizmor with network advisories, and nightly
runs lychee/zizmor online — the local gate stays deterministic (`--offline`) on purpose.

## Owner settings checklist (HUMAN-only; agents are hook-blocked from all of it)

**Script:** [`scripts/setup-repo-settings.sh`](../scripts/setup-repo-settings.sh) automates
items 1–5 below (`bash scripts/setup-repo-settings.sh`, idempotent, read-back verification
included) and item 6 (`--phase2`, self-guarded: refuses until `ci-required` has reported
green on a real PR). The Actions allowlist/SHA-pin checkbox in item 3 and items 7–8 stay
manual UI steps.

Now (with this branch's merge):

1. **Secret scanning + push protection** — Settings → Advanced Security → enable
   *Secret scanning*, *Push protection*, and *Scan for non-provider patterns*. CLI:
   `gh api -X PATCH repos/PranavMishra28/detent --input -` with
   `{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"},"secret_scanning_non_provider_patterns":{"status":"enabled"}}}`.
   Second layer only — local gitleaks (pre-commit + `make secrets`) stays primary.
2. **Dependabot alerts + security updates** — same pane; or
   `gh api -X PUT repos/PranavMishra28/detent/vulnerability-alerts` and
   `gh api -X PUT repos/PranavMishra28/detent/automated-security-fixes`.
3. **Actions posture** — Settings → Actions → General: *Allow PranavMishra28, and select
   non-PranavMishra28, actions* with allowlist `astral-sh/setup-uv@*` (github-owned actions
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
8. Retention stays 90 days (public max); enable **Private vulnerability reporting**.

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

Reconciliation rule: CI-R3's public-repo findings supersede W7's private-repo assumptions.

- **Cut `gitleaks/gitleaks-action` job** (W7 security.yml): redundant with the `make
  secrets` parity scan already inside `make check`; W7 itself named the parity scan as the
  keeper if the redundancy chafed.
- **Cut `zizmor-action` and separate `security.yml`/`docs-check.yml` workflows**: replaced
  by the pinned zizmor/actionlint binaries from the one bootstrap pin table (offline in
  `make check`, online in `workflow-security`/nightly) and by the single always-running
  ci.yml — required-check semantics on a public repo make the aggregator pattern, not
  separate path-filtered workflows, the correct shape. Two fewer third-party actions.
- **Cut W7's workflow-level `on.paths` filters** (ci.yml): they break required checks
  (pending-forever trap); replaced by the `changes` job + aggregator.
- **Cut Postgres service containers from committed YAML**: no code exists; the digest pin
  would rot unused. The T2/T3 bodies are documented (here and in workflow comments) and
  land with the code at M3.
- **Cut the GitHub Pro pairing recommendation** (W7 §2): rulesets/environments are free on
  public repos; Pro buys nothing while public.
- **Deferred: PR template** — the owner is the sole author today; a checklist nobody else
  reads is ceremony. Adopt at code landing or first external contributor (whichever first).
- **Deferred: CODEOWNERS, auto-labeling, Scorecard, README badges** — per CI-R2/CI-R3
  rulings (solo repo; Scorecard needs a scoped `security-events: write` exception that
  deserves its own decision at M3).
- **Deferred: Cursor CLI diagnostic workflow** (CI-R2 §5): its guardrails are designed, but
  it requires a `CURSOR_API_KEY` secret — which violates the no-repo-level-secrets rule
  until an owner-created environment holds it — and the vendor installer has no published
  stable checksum to pin. Revisit when both close.
- **`nightly-failure` template placement**: lives in `.github/ISSUE_TEMPLATE/` with
  frontmatter so the same file serves manual filing; the workflow strips frontmatter and
  fills placeholders from trusted context only.
