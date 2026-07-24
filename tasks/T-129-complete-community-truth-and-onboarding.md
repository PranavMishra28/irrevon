# T-129: Complete community, truth, and onboarding documentation

---
id: T-129
status: done
depends_on: [T-124]
invariant: "master doc §5.4, §9, §12, and §13; preserve honest public status, privacy disclosure, and human-only external gates"
---

## Objective

Make the repository's community channels, source onboarding, operations guidance,
licensing status, deployment truth, and public-history limitation accurate and
actionable without changing any external service.

## Why

The launch branch needs a clean stranger journey and prepared GitHub Discussions
links, while current read-back still shows Discussions disabled, a stale public
Vercel deployment, and unresolved owner-only privacy and repository-settings
actions. Internal nightly triage must also be removed from the public issue
chooser.

## Context — read these first

- `AGENTS.md`
- `README.md`
- `SUPPORT.md`
- `CONTRIBUTING.md`
- `docs/project-status.md`
- `docs/security-policy.md`
- `docs/discoverability.md`
- `docs/operations.md`
- `docs/ci.md`

## Scope

**Allowed to write:** this task file; `README.md`; `SUPPORT.md`;
`CONTRIBUTING.md`; `LICENSING.md`; `.github/ISSUE_TEMPLATE/config.yml`;
`.github/ISSUE_TEMPLATE/question.yml`;
`.github/ISSUE_TEMPLATE/nightly-failure.md`; a replacement workflow-internal
nightly template path; `.github/workflows/nightly.yml`;
`docs/project-status.md`; `docs/project-status.json`;
`docs/security-policy.md`; `docs/discoverability.md`; `docs/operations.md`;
`docs/ci.md`; matching generated site mirrors; `scripts/check-public-truth.py`;
and focused tests for those surfaces.

**Forbidden:** every other path; `docs/master-doc.md`; accepted ADR content;
frozen preregistration content; product/site files other than generated
repository-document mirrors; release/package implementation; external settings;
history rewriting; sensitive historical values; provider calls; scientific
freezes or results; publication; deployment; and commits.

## Acceptance criteria

- [x] README source quickstart, Workbench staging, and synthetic demo evidence
      handoff are copy-pasteable and describe the alpha candidate honestly.
- [x] Community documentation prepares GitHub Discussions Community/Q&A/Ideas
      links but explicitly refuses to claim availability until the owner enables
      and reads back Discussions.
- [x] Issues remain the route for bugs, documentation, benchmark integrity, and
      scoped proposals; vulnerabilities always use private reporting; no email
      address or support SLA is invented.
- [x] A source user can run a documented synthetic continuous-worker exercise
      and understand its non-production boundary.
- [x] The internal nightly-failure body no longer appears in the public issue
      chooser.
- [x] Public truth records the current stale Vercel deployment without claiming
      cryptographic provenance, and preserves the history accept-or-rewrite
      owner decision.
- [x] Current GitHub-setting read-back is accurately recorded without mutating
      it.
- [x] Focused public-truth and documentation checks pass.

## Required validation

```text
python3 scripts/check-public-truth.py
node site/scripts/sync-docs.mjs --check
make links
make docs
git diff --check
```

## Documentation updates

Update the in-scope public community, onboarding, operations, licensing,
deployment-truth, security, and CI surfaces plus their generated site mirrors.

## Human review triggers — stop and ask if:

- Enabling Discussions, changing repository settings, deploying Vercel,
  rewriting history, publishing, or closing any external/legal/scientific gate
  becomes necessary.
- A scan exposes a confidential value rather than a sanitized path-level
  finding.
- A required correction conflicts with an accepted ADR or frozen document.

## Definition of done

Every criterion is checked; focused validation output is recorded; no
out-of-scope file is written; external state remains unchanged; and the task is
set to `done`.

## Completion evidence — 2026-07-24

- `python3 scripts/check-public-truth.py` passed with alpha-candidate,
  Discussions, private-reporting, stale-deployment, owner-settings,
  public-history, source-Workbench, and synthetic-worker contracts.
- `uv run pytest -q tests/scripts/test_nightly_contract.py` passed (3 tests).
- `actionlint .github/workflows/nightly.yml` passed.
- `node site/scripts/sync-docs.mjs --check` reported all 41 rendered documents
  in sync.
- `make links` checked 422 links with 0 errors; `make docs` was an up-to-date
  no-op.
- `make check` passed, including schema, gitleaks current-tree/history,
  integrity, public-truth, frozen-file, asset, dependency-notice, and benchmark
  gates. The optional private `.tripwords` scan was absent and therefore
  skipped, as disclosed by the gate.
- Ruff lint/format checks and `git diff --check` passed for the focused Python
  files.

No GitHub setting, public history, release, provider, benchmark, package index,
or Vercel deployment was changed.

## Integrator finding

`CODE_OF_CONDUCT.md` still refers safe public conduct questions to the removed
question issue form. That file is outside T-129 scope. A separate bounded edit
must route safe public follow-up to the verified Community Discussion after
Discussions is enabled, retain GitHub platform reporting/blocking tools, and
state honestly that no project-specific confidential conduct channel exists.
It must not reuse private vulnerability reporting or invent an email/private
channel.
