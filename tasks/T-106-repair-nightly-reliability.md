# T-106: Repair the nightly reliability gates

---
id: T-106
status: done
depends_on: [T-105]
invariant: "docs/ci.md — nightly extends the local gates without weakening them; ADR-0018 — distributable artifacts include the staged workbench and install without Node"
---

## Objective

Make the scheduled nightly exercise the intended online-link and wheel/sdist checks
reliably on Linux, and make its failure reporter work without an undocumented repository
label prerequisite.

## Why

Scheduled run 30002711831 on commit `85358fd` exposed three infrastructure defects rather
than product-test failures: the online lychee command omitted the local gate's exclusions
and remaps, the Node-less smoke container could not reach the loopback-bound compose
Postgres through the Linux host bridge, and the reporter required an absent label. A red
nightly cannot be accepted as release evidence until these are repaired and locally
reproduced.

## Context — read these first

- `docs/ci.md` (nightly map and troubleshooting)
- `.github/workflows/nightly.yml`
- `Makefile` (`links`, `dist-smoke`, `py-db-up`)
- `scripts/dist-smoke.sh`
- `docker-compose.yml`

## Scope

**Allowed to write:** `tasks/T-106-repair-nightly-reliability.md`, `.github/workflows/nightly.yml`,
`.github/ISSUE_TEMPLATE/nightly-failure.md`, `Makefile`, `scripts/dist-smoke.sh`,
`docs/benchmark.md`, `docs/ci.md`, and a narrowly scoped test under `tests/scripts/`.

**Forbidden:** product runtime code; schemas; benchmark fixtures, metrics, baselines, or
freeze controls; repository settings or labels; workflow triggers; publication; weakening
the offline or online link checks; changing the loopback-only host exposure of Postgres.
Anything else is out of scope.

## Acceptance criteria

- [x] The online link target uses the same source exclusions and Vite public-directory
      remaps as `make links`, while still checking external URLs.
- [x] The stale The Register URL is corrected; the SEC endpoint's documented bot rejection
      is handled narrowly without accepting arbitrary 4xx responses.
- [x] `make dist-smoke` reaches Postgres through the compose network on Linux without
      exposing Postgres beyond host loopback.
- [x] Failure reporting deduplicates one open issue without requiring a pre-created label,
      and consumes no untrusted event text.
- [x] A regression test asserts these workflow/script contracts.
- [x] `make check` passes.

## Required validation

```sh
make check
uv run pytest tests/scripts -p no:cacheprovider
make dist-smoke
actionlint .github/workflows/nightly.yml
zizmor --offline --persona=pedantic .github/workflows/nightly.yml
```

## Documentation updates

Update `docs/ci.md` to remove the label prerequisite and record the compose-network smoke
topology and online-link parity rule.

## Human review triggers — stop and ask if:

- A fix would require changing repository labels/settings, workflow permissions, the
  Postgres host binding, or accepting a broad class of failed HTTP statuses.
- The smoke fix requires a different database image or digest.
- A failing external link supports a scientific claim and no equally authoritative source
  exists.

## Definition of done

All criteria checked; validation output attached; documentation updated; no writes outside
the allowed scope; status set to `done`.

## Completion record

Completed 2026-07-23. Validation:

- `make check` — passed.
- `uv run pytest tests/scripts -p no:cacheprovider` — 8 passed.
- `make links-online` — 340 links considered, 339 OK, one exact SEC exclusion, zero errors.
- `make dist-smoke` — wheel and sdist legs passed in a Node-less Python 3.13 container.
- `actionlint .github/workflows/nightly.yml` — passed.
- `zizmor --offline --persona=pedantic .github/workflows/nightly.yml` — no findings.
