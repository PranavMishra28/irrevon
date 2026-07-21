# Tasks — bounded work orders for agents

Tasks are work orders with a lifecycle; durable knowledge lives in `docs/`. All agent work in
this repo happens through a task file here (AGENTS.md working protocol): one task per agent
session, scope enforced, exit criteria verifiable.

## Process

- Files are `T-NNN-short-title.md`; ids chronological by creation, never reused. Completed
  tasks are kept, not deleted (append-only records policy, master doc §12.5).
- **Statuses** (frontmatter): `draft → ready → in-progress → done | blocked`.
  `blocked-human-review` marks a task whose output awaits ratification.
- Cross-task sequencing and gates live in [docs/execution-plan.md](../docs/execution-plan.md),
  not here.
- An acceptance criterion is verifiable or it is not a criterion: name the exact command and
  the observable result, and include at least one failure/edge case.
- Standing rules live in AGENTS.md — do not repeat them in tasks; task files carry only
  task-specific scope and criteria.
- If a task turns out under-specified or requires out-of-scope edits: stop, set `blocked`,
  record why, and flag the human. Never widen your own scope.

## Template (12 fields)

```markdown
# T-NNN: <imperative title, one line>

---
id: T-NNN
status: draft            # draft | ready | in-progress | done | blocked | blocked-human-review
depends_on: []           # task ids that must be done first
invariant: "<master doc §x.y the task must protect>"   # or "none"
---

## Objective
One sentence: the smallest useful outcome this task produces.

## Why
1–3 sentences: which master-doc section / ADR / phase motivates this now.

## Context — read these first
- <repo-relative paths with sections>

## Scope
**Allowed to write:** <explicit paths>
**Forbidden:** <paths + behaviors>. Anything not listed as allowed is out of scope.

## Acceptance criteria
- [ ] <command> exits 0 and <specific observable result>
- [ ] <edge or failure case>: given <input>, <exact expected behavior>
- [ ] `make check` passes

## Required validation
Exact commands to run; attach output on completion.

## Documentation updates
Files that must change with this task (status lines, indexes), or "none".

## Human review triggers — stop and ask if:
- <condition>

## Definition of done
All criteria checked; validation output attached; documentation updates made; no writes
outside allowed scope; status set.
```

Field count: objective · why · context · allowed scope · forbidden scope · dependencies
(frontmatter) · invariant (frontmatter) · acceptance criteria · required validation ·
documentation updates · human-review triggers · definition of done.
