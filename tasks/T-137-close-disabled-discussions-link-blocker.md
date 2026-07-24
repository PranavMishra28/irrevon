# T-137: Close the disabled-Discussions link blocker

---
id: T-137
status: done
depends_on: [T-129, T-135]
invariant: "public community routes must describe only enabled, verified surfaces; security reports remain private"
---

## Objective

Remove public links to disabled GitHub Discussions destinations while
preserving a concise, explicit owner gate for enabling and verifying the
intended future categories.

## Why

GitHub Discussions is currently disabled. Category URLs and issue-chooser
contact links therefore lead users to unavailable destinations and make the
launch documentation less truthful.

## Scope

**Allowed to write:** this task file; `README.md`; `SUPPORT.md`;
`CONTRIBUTING.md`; `CODE_OF_CONDUCT.md`;
`.github/ISSUE_TEMPLATE/config.yml`; `docs/project-status.md`;
`docs/project-status.json`; `docs/security-policy.md`; `docs/ci.md`;
`docs/discoverability.md`; affected generated documentation mirrors;
`scripts/check-public-truth.py`; and focused tests.

**Forbidden:** every other path, including site layout/navigation; GitHub
repository settings; provider calls; secrets; invented email or response SLA;
publication; deployment; history rewriting; and commits.

## Acceptance criteria

- [x] No public document or issue chooser exposes a clickable GitHub
      Discussions or category destination while Discussions is disabled.
- [x] No broken public Community link remains.
- [x] The owner gate names `Announcements`, `Q&A`, `Ideas and feedback`, and
      `Show and tell`, and requires enablement, category creation, a pinned
      welcome post, and URL read-back before future links are exposed.
- [x] Existing GitHub Issues and private-vulnerability-reporting routes remain
      accurate.
- [x] No repository setting is changed and no email or response SLA is
      invented.
- [x] Link, public-truth, generated-mirror, repository, and diff checks pass.

## Required validation

```text
lychee --offline --include-fragments --no-progress .
python3 scripts/check-public-truth.py
node site/scripts/sync-docs.mjs --check
make check
git diff --check
```

## Human review triggers — stop and ask if:

- The fix requires enabling Discussions, creating a category, pinning a post,
  changing repository settings, or publishing any external content.

## Definition of done

Unavailable Discussion destinations are absent from public copy, future
enablement is recorded as an explicit owner gate, truthful issue/security
routes remain, all validations pass, and this task is set to `done`.

## Completion evidence

- `make links` passed: 423 links checked, 305 valid, 0 errors, with 118
  configured exclusions.
- `python3 scripts/check-public-truth.py` passed and now rejects any
  repository-Discussion URL on the scoped public surfaces while Discussions is
  disabled.
- `node site/scripts/sync-docs.mjs --check` passed with all 41 rendered
  documentation mirrors current; the CI and security-policy mirrors were
  regenerated.
- Ruff formatting/lint and JSON parsing passed for the changed truth gate and
  status document.
- `make check` passed, including link, schema, secret, integrity, public-truth,
  frozen-artifact, asset, third-party, and benchmark-integrity gates.
- `git diff --check` passed.
- `site/src/layouts/Base.astro` was not edited; T-135's `Contribute` navigation
  remains outside this task.
- No repository setting, external service, email/SLA posture, commit, publish,
  or deployment action was changed.
