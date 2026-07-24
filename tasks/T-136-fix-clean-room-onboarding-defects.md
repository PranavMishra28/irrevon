# T-136: Fix the final clean-room onboarding defects

---
id: T-136
status: done
depends_on: [T-133]
invariant: "master doc §7 and §9; preserve migration/runtime authority separation, least privilege, and synthetic-only validation"
---

## Objective

Fix the five reproducible onboarding and synthetic-operator defects found by
the T-133 hostile clean-room review.

## Why

The end-to-end source journey succeeds, but its success guidance can overwrite
local configuration, one error names the wrong generated file, the synthetic
server looks crashed on Ctrl-C, doctor authority is under-disclosed in the
README, and one destructive recovery recipe leaves PostgreSQL stopped.

## Context — read these first

- `tasks/T-133-hostile-clean-room-onboarding-review.md`
- `src/irrevon/cli/init_cmd.py`
- `src/irrevon/cli/demo.py`
- `src/irrevon/adapters/refdest_server.py`
- `README.md`
- `site/src/content/guides/getting-started.md`

## Scope

**Allowed to write:** this task file; `src/irrevon/cli/init_cmd.py`;
`src/irrevon/cli/demo.py`; `src/irrevon/adapters/refdest_server.py`;
`README.md`; `site/src/content/guides/getting-started.md`; and focused tests
for init, demo, reference-destination process behavior, and documentation.

**Forbidden:** every other path; product-scope changes; provider/live calls;
external settings; secrets; publication; deployment; history rewriting; and
commits.

## Acceptance criteria

- [x] A successful migration init prints only the safe doctor next step.
- [x] First-run init guidance never implies overwriting an existing `.env`.
- [x] Missing demo migration authority names `.env.example` and gives a correct
      copy/source or direct-export remedy.
- [x] The synthetic reference server handles Ctrl-C without a traceback,
      closes its server resource, and has a focused process regression.
- [x] README discloses doctor's rolled-back write probe.
- [x] The stale-volume recipe warns about deletion and restarts PostgreSQL
      before init.
- [x] Focused tests, public truth, documentation, repository, and diff checks
      pass.

## Required validation

```text
uv run pytest -q <focused tests>
python3 scripts/check-public-truth.py
make check
git diff --check
```

## Documentation updates

Update only the scoped README and generated-site getting-started guide.

## Human review triggers — stop and ask if:

- A fix requires weakening authority separation, adding a provider call,
  changing product scope, or mutating an external service.

## Definition of done

All five defects have regressions, validations pass, no out-of-scope file is
written, no external state changes, and the task is set to `done`.

## Completion evidence

- `uv run pytest -q tests/cli/test_init_config.py tests/cli/test_demo_security.py
  tests/adapters/test_refdest_server_process.py
  tests/scripts/test_onboarding_guidance.py` — 32 passed.
- Scoped Ruff formatting and lint checks passed.
- `python3 scripts/check-public-truth.py` passed.
- `node site/scripts/sync-docs.mjs --check` passed with all 41 rendered
  documentation mirrors current.
- `make check` passed, including schema, secret, integrity, public-truth,
  frozen-artifact, asset, third-party, and benchmark-integrity gates.
- `git diff --check` passed.
- No provider calls, external mutations, commits, or publication actions were
  performed.
