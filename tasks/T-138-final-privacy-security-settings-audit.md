# T-138: Final privacy, security, and settings audit

---
id: T-138
status: done
depends_on: [T-134]
invariant: "master doc §9 and §12.3; preserve secret safety, truthful public-history disclosure, and human-only repository controls"
---

## Objective

Perform a final read-only audit of public-history privacy, shipped artifacts,
dependency/workflow security, and the repository settings that gate launch.

## Scope

**Allowed to write:** this task file only.

**Forbidden:** every implementation, documentation, generated, workflow, or
configuration file; commits; tags; releases; publication; deployments;
repository/settings mutations; history rewriting; credentials; and sensitive
value output.

## Acceptance criteria

- [x] Read authenticated repository settings where the API permits: rulesets,
      collaborators/CODEOWNERS, Actions policy, security features, Discussions,
      releases, and environments.
- [x] Run sanitized reachable-history, current-tree, media/archive, dependency,
      and workflow security checks without reproducing sensitive values.
- [x] Confirm public-history wording preserves the known exposure and does not
      overclaim automated scanner completeness.
- [x] Separate exploitable shipped Critical/High findings from OpenSSF posture
      alerts and owner-only launch blockers.
- [x] Record exact sanitized evidence and no external or implementation changes.

## Required validation

```text
gitleaks git --no-banner --redact .
python3 scripts/check-public-data.py
python3 scripts/check-public-truth.py
uv run --locked pip-audit
web production dependency audit
site production dependency audit
actionlint .github/workflows/*.yml
zizmor --offline --persona=pedantic .github/workflows/
git diff --check
```

## Human review triggers

- Any command would print a sensitive historical value instead of only a count,
  path class, commit identifier, or redacted finding.
- Any missing API permission would require a settings change, broader token, or
  credential inspection.
- Any remediation would require an implementation or external-state change;
  report it instead.

## Definition of done

The live settings and repository evidence are reconciled into a sanitized,
severity-separated verdict, exact owner blockers are recorded, no forbidden
state changes occur, and this task is marked done.

## Audit record — 2026-07-24

All API calls in this section were authenticated, read-only calls against
`PranavMishra28/irrevon`. This audit changed no GitHub setting and did not
publish, deploy, tag, release, commit, push, or rewrite history.

### Severity-separated verdict

**Known exploitable shipped Critical/High findings: 0.** The frozen production
Python export, both production JavaScript dependency graphs, Dependabot alerts,
and CodeQL alerts produced no known vulnerability in those classes. This is a
point-in-time dependency/static-analysis result, not a proof that the product is
vulnerability-free.

**OpenSSF posture alerts: 10, all from Scorecard and none from CodeQL.** The
three `high` findings are `BranchProtectionID`, `CodeReviewID`, and
`MaintainedID`; the six `medium` findings are `FuzzingID`,
`PinnedDependenciesID` (three workflow-command instances), `SASTID`, and
`SecurityPolicyID`; the one `low` finding is `CIIBestPracticesID`. These are
repository/process posture signals, not evidence of an exploitable shipped
Critical/High vulnerability. In particular, the maintained and code-review
scores reflect the young repository and its observed review history.

**Launch blockers remain.** The repository is not settings-complete for the
documented public launch: history exposure still requires an explicit owner
choice; Discussions/categories are absent; release/sandbox/benchmark protected
environments are absent; the existing Production environment is unprotected;
the main ruleset retains an always-on repository-role bypass and zero-review
posture; immutable releases and GitHub-level Actions SHA enforcement are off;
and the exact locked `pip-audit` command is not provisioned by `uv.lock`.

### Public-history privacy boundary

The wording is truthful and conservatively scoped:

- `docs/security-policy.md` says the automated checks cover defined secret,
  credential-bearing DSN, machine-path, environment-file, and media-metadata
  patterns; says they are not semantic PII detectors; and explicitly says they
  do not prove the absence of all historical PII.
- `docs/security-policy.md`, `docs/project-status.md`, and
  `docs/project-status.json` preserve the known pre-redaction personal-prose
  exposure and the exact owner choice: knowingly accept the exposure or
  coordinate a human-only history rewrite with complete public-ref
  replacement.
- `scripts/check-public-data.py` itself ends with “not an exhaustive
  historical-PII audit.” Its successful run reported two allowlisted
  historical blobs without printing their contents.

No sensitive historical value was read into this record, quoted, or
reproduced. No history rewrite was attempted.

### Live repository settings

| Surface | Authenticated readback | Assessment |
|---|---|---|
| Repository | public; default branch `main` | Expected public posture. |
| Collaborators | one collaborator, the repository owner, role `admin` | No third-party collaborator found. |
| CODEOWNERS | global owner plus explicit ownership for `.github`, migrations, schemas, decisions, preregistration, engine, benchmark, security, and license surfaces | File exists, but the ruleset does not require its review. |
| Main ruleset | active `main-protection-phase1`; deletion and non-fast-forward denied; `ci-required` required; strict/up-to-date mode off; zero approvals; code-owner review off; last-push approval off; stale-review dismissal off; thread resolution off; one repository-role actor can bypass `always` | The only collaborator is an admin and the active ruleset preserves an always-on repository-role bypass, so owner direct-push/bypass remains possible. |
| Actions policy | Actions enabled; all actions allowed; GitHub SHA enforcement off | Workflow files pass the repository's offline pinning audit, but the owner-level allowlist/enforcement defense is absent. |
| Workflow token/fork policy | default workflow permission `read`; workflows cannot approve PR reviews; all external contributors require fork approval | Good least-privilege defaults. |
| Secret scanning | secret scanning and push protection enabled; zero open alerts | Good baseline. Non-provider patterns and validity checks are disabled. |
| Dependabot | security updates enabled; zero open alerts | Every configured ecosystem has an explicit `applies-to: security-updates` group. The separate repository-level grouped-security UI toggle is not exposed by the audited REST readback and still needs owner verification. |
| Private vulnerability reporting | enabled | Ready for private reports. |
| CodeQL/default setup | configured; latest Actions, Python, and JavaScript/TypeScript analyses succeeded with empty errors | Zero open CodeQL alerts. The API's default-setup `languages` array was empty, so the successful per-language analyses are the stronger observed evidence. |
| Discussions | disabled; zero categories | Owner launch setup remains undone. |
| Releases/tags | zero releases and zero tags | No accidental publication found. |
| Immutable releases | disabled; not enforced by the owner | Owner launch hardening remains undone. |
| Environments | only `Preview` and `Production`; both have no protection rules or branch policy | `release`, `sandbox`, and `benchmark` are absent. `Production` exists but is unprotected. |

Classic branch protection returned “not protected”; the active ruleset above is
the actual branch-protection mechanism. The selected-actions endpoint was not
applicable because the repository currently permits all actions.

### Sanitized scanner and dependency evidence

| Check | Result |
|---|---|
| `gitleaks git --no-banner --redact .` | pass; 146 reachable commits, approximately 8.47 MB, no leaks found |
| `gitleaks dir --no-banner --redact .` | pass; approximately 10.94 MB, no leaks found |
| `python3 scripts/check-public-data.py` | pass; two allowlisted historical blobs; explicitly non-exhaustive for historical PII |
| `python3 scripts/check-public-data.py --include-generated` | pass; current tree plus existing `dist`, `site/dist`, and staged workbench outputs |
| `python3 scripts/check-public-truth.py` | pass; launch status, community posture, and 13-schema inventory agree |
| Media inventory | no MP4/MOV/M4V artifact in the current tree/build outputs; generated PNG metadata passed the public-data gate |
| Archive checksums | wheel, sdist, and SPDX checksum entries all verified |
| Extracted archive scan | pass; 438 extracted files, zero gitleaks findings and zero defined machine-path/password-DSN matches |
| Frozen Python production graph | supplementary audit of the hash-bearing `uv export --frozen --no-dev --no-emit-project` graph with `pip-audit 2.10.0`: 8 dependency records, zero known vulnerabilities |
| Workbench production graph | Node 24.5.0 / pnpm 10.28.1 `pnpm audit --prod`: 28 production/optional dependencies, zero info/low/moderate/high/critical vulnerabilities |
| Site production graph | Node 24.5.0 / pnpm 10.28.1 `pnpm audit --prod`: 308 production/optional dependencies, zero info/low/moderate/high/critical vulnerabilities |
| `actionlint .github/workflows/*.yml` | pass, no findings |
| `zizmor --offline --persona=pedantic .github/workflows/` | pass, no findings |
| `git diff --check` | pass |

The required literal command `uv run --locked pip-audit` failed closed before
an audit because `pip-audit` is not a project or dependency-group executable in
`uv.lock`; it did not resolve or install anything. The supplementary audit
above froze the project input with `uv export --frozen` and audited the
hash-bearing production graph from outside the repository. That result covers
the current production graph, but it does not satisfy the repository's intended
fully locked validator provenance. Adding an exact-constrained `pip-audit` to
an appropriate dependency group and lockfile is a separate implementation task
outside this read-only audit.

### Exact owner and follow-up blockers

1. **History privacy:** choose knowingly to accept the documented historical
   exposure or coordinate the human-only complete history rewrite/ref
   replacement. Do not call the automated scan proof of PII absence.
2. **Ruleset/direct push:** remove or narrowly constrain the always-on
   repository-role bypass; require at least one approval, code-owner review,
   last-push approval, stale-review dismissal, resolved conversations, and
   strict/up-to-date required checks as the owner judges appropriate.
3. **Actions:** change from “all actions allowed” to the intended allowlist and
   enable GitHub's SHA-pinning enforcement. Keep the already-good read-only
   default token permission and all-external-contributor fork approval.
4. **Security features:** enable non-provider secret patterns and validity
   checks if available for the repository, and verify the repository-level
   grouped Dependabot security-updates setting in the UI.
5. **Community:** enable Discussions, create the reviewed categories, and
   read back their URLs before publishing the welcome material.
6. **Release governance:** enable immutable releases before the first
   publication; create/protect the documented `release`, `sandbox`, and
   `benchmark` environments; and add protection/branch policy to Production.
7. **Locked Python audit:** land a separate bounded implementation task that
   exact-constrains and locks the audit executable, then make the literal
   `uv run --locked pip-audit` validation pass.
8. **OpenSSF posture:** evaluate the non-exploit posture findings separately:
   review/fuzzing/SAST/security-policy/badge coverage and workflow-command
   dependency hashes. Repository age by itself is not remediable.

No remediation in this list was performed by T-138.
