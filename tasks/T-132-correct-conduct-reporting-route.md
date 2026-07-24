# T-132: Correct the public conduct-reporting route

---
id: T-132
status: done
depends_on: [T-129]
invariant: "master doc §12.4; preserve truthful community enforcement channels without conflating conduct and security"
---

## Objective

Replace the removed question-form reference in the Code of Conduct with the
truthful, owner-gated Community Discussion route.

## Why

T-129 moved usage questions to prepared GitHub Discussions and removed the
question issue form. The Code of Conduct must not point to that dead form or
misuse private vulnerability reporting for conduct reports.

## Context — read these first

- `AGENTS.md`
- `CODE_OF_CONDUCT.md` §Reporting an Issue
- `SUPPORT.md`

## Scope

**Allowed to write:** this task file and `CODE_OF_CONDUCT.md`.

**Forbidden:** every other path; any new private channel, email address,
response SLA, GitHub setting change, publication, deployment, history rewrite,
or vulnerability-reporting change.

## Acceptance criteria

- [x] GitHub content directs reporters to GitHub reporting and blocking tools.
- [x] A safe public report may use the prepared Community Discussion only after
      Discussions and that category are enabled and verified.
- [x] The policy explicitly states that no project-specific confidential
      conduct-reporting channel exists.
- [x] Conduct reports never route to private vulnerability reporting.
- [x] Link, public-truth, and diff checks pass.

## Required validation

```text
make links
python3 scripts/check-public-truth.py
git diff --check
```

## Documentation updates

Update only the reporting paragraph in `CODE_OF_CONDUCT.md`.

## Human review triggers — stop and ask if:

- A confidential project channel, email address, SLA, or repository-setting
  change is required.

## Definition of done

The dead route is removed, the truthful external-state gate remains explicit,
validation passes, only the two allowed paths are written, and the task is set
to `done`.

## Completion evidence — 2026-07-24

- `make links` checked 423 links with 0 errors.
- `python3 scripts/check-public-truth.py` passed.
- `git diff --check` passed.

No private channel, email, SLA, vulnerability route, GitHub setting, commit,
publication, deployment, or history state was created or changed.
