# T-133: Hostile-review the clean-room onboarding journey

---
id: T-133
status: done
depends_on: [T-129]
invariant: "master doc §7 and §9; preserve explicit migration authority, least privilege, synthetic evidence, and honest alpha boundaries"
---

## Objective

Verify the README onboarding and synthetic worker journey from a stranger's
clean environment, then report only reproducible defects and minimal fixes.

## Why

Launch onboarding must work without repository knowledge, a hosted database,
provider credentials, or hidden setup. The source-built Workbench and demo
evidence handoff cross Python, Docker, PostgreSQL, Node, and generated-file
boundaries that need an adversarial final read-back.

## Context — read these first

- `README.md` only for the initial user journey
- Referenced implementation or tests only after reproducing a failure or
  verifying an asserted boundary

## Scope

**Allowed to write:** this task file only. Temporary files outside the
repository may be created for clean-room validation.

**Forbidden:** every other repository path; provider/live calls; reading
secrets; external settings; publication; deployment; history rewriting;
commits; and any mutation outside isolated local test resources.

## Acceptance criteria

- [x] Command order and prerequisites are verified from a clean source copy.
- [x] Migration/runtime/read authority separation and demo DSN/artifact
      handoff are verified.
- [x] Source Workbench staging, doctor semantics, and the bounded synthetic
      worker exercise are checked.
- [x] Public links and alpha limitations are reviewed without treating gated
      external channels as live.
- [x] Findings name exact files/lines, evidence, impact, and the smallest safe
      fix.
- [x] Temporary validation performs no provider/live call or external mutation.

## Required validation

Run the README source journey and applicable worker/Workbench checks in an
isolated temporary copy; record exact pass/fail evidence and run
`git diff --check` for the task record.

## Documentation updates

None; this task is an audit record only.

## Human review triggers — stop and ask if:

- Validation would require a provider credential, external account, deployment,
  repository setting, publication, or sensitive-value access.

## Definition of done

The audit is complete, findings are substantiated and sanitized, no repository
file except this task changed, temporary resources are stopped, and the task is
set to `done`.

## Clean-room evidence — 2026-07-24

The current working tree was copied to an isolated temporary directory with
Git metadata, environment files, virtual environments, dependency directories,
build output, and staged Workbench assets excluded. No `.env*` content or
credential was read.

The README sequence succeeded with an isolated PostgreSQL 17 container on an
alternate loopback port:

- `uv sync --locked` selected Python 3.13.13 and installed the unpublished
  `0.1.0` source package.
- First `uv run irrevon init` created `irrevon.toml`, `compose.yaml`, and
  `.env.example` without attempting migrations.
- The second init, given an explicit migration-only admin DSN, applied all five
  migrations. `irrevon doctor` confirmed the runtime role could perform its
  rolled-back write probe and the serve role was read-only.
- `irrevon demo --seed 42 --keep --artifact
  ./irrevon-demo-artifact.json` completed both synthetic legs, created one
  Irrevon-side destination effect versus two in the B5 contrast, and printed
  the kept demo DSN plus artifact-aware serve command.
- With Node 24.18.0, `corepack enable` and `make web-build dist-stage`
  completed. The loopback server reported `read_role=irrevon_read`,
  `workbench_assets=true`, and `demo_artifact=true`; the HTML, health, and demo
  artifact endpoints returned 200, and the artifact reported 11 events with
  `contrast_holds=true`.
- The documented reference destination plus three-cycle worker exercise
  completed with empty gauges, two synthetic sweeps, a cycle-3 health document,
  and no provider call.
- GitHub read-back confirmed Issues and private vulnerability reporting are
  enabled while Discussions is disabled. The README explicitly treats the
  Discussion URLs as a pre-merge owner gate and the public site as stale, so
  neither is misrepresented as current.

The isolated container, network, and volume were removed. The temporary source
copy was moved to system trash after validation.

## Findings

### F1 — successful second init prints a destructive, stale next step

- **Evidence:** `src/irrevon/cli/init_cmd.py:143-152` prints the same
  `cp .env.example .env ... docker compose up ... init` instruction even after
  migrations have applied. The clean-room second init reproduced it.
- **Impact:** a user following the success message can overwrite an already
  configured `.env` and rerun completed bootstrap work. This is especially
  unsafe once a local operator has replaced placeholders.
- **Minimal fix:** when `migrations_applied is not None`, print only
  `next: irrevon doctor`. Reserve the full bootstrap instruction for the
  scaffold/database-unavailable case, and make any copy instruction
  non-overwriting or explicitly first-run-only.

### F2 — missing demo authority names a file init does not generate

- **Evidence:** without `IRREVON_MIGRATION_DSN`, the demo exits 1 with the
  message at `src/irrevon/cli/demo.py:246-249`: “source the .env generated by
  irrevon init”. Init generates `.env.example`; the README requires the user to
  copy it to `.env`.
- **Impact:** a user diagnosing the most likely demo setup failure is told to
  find a generated file that does not exist until they create it.
- **Minimal fix:** say “set `IRREVON_MIGRATION_DSN`, or copy `.env.example` to
  `.env` and source it as shown in the README quickstart.”

### F3 — the documented Ctrl-C shutdown emits a traceback

- **Evidence:** `docs/operations.md:67-68` tells the user to stop the synthetic
  reference destination with Ctrl-C. The command reaches the unguarded
  `serve_forever()` call at
  `src/irrevon/adapters/refdest_server.py:129-133`; clean-room shutdown emitted
  a full `KeyboardInterrupt` traceback and exited 130.
- **Impact:** the first operator exercise ends looking like a crash, obscuring
  whether cleanup was expected and undermining the otherwise clean synthetic
  walkthrough.
- **Minimal fix:** catch `KeyboardInterrupt`, close the server in `finally`, and
  exit without a traceback. Add a focused CLI/process test for graceful
  interrupt.

### F4 — README does not disclose that doctor performs a write probe

- **Evidence:** the README executes doctor at `README.md:51-52` but does not
  explain its authority. The CLI path documents and performs a rolled-back
  temporary-table write probe (`src/irrevon/cli/doctor.py:325-334`); the deeper
  guide explains this correctly at
  `site/src/content/guides/getting-started.md:45-55`.
- **Impact:** an enterprise evaluator may reasonably interpret “doctor” as a
  read-only diagnostic and run it with an account that must not exercise write
  privileges.
- **Minimal fix:** add one README sentence beside the command: doctor is
  non-destructive but not strictly read-only; it performs a rolled-back write
  probe using the runtime/operator role.

### F5 — stale-database recovery omits restarting PostgreSQL

- **Evidence:** `site/src/content/guides/getting-started.md:53-55` recommends
  `docker compose down -v && uv run irrevon init`. After `down -v`, init does
  not start Docker; it treats an unreachable database as a non-fatal scaffold
  state, so the recovery does not restore a usable environment.
- **Impact:** the exact remediation offered for a stale database leaves the
  database stopped and requires undocumented diagnosis.
- **Minimal fix:** use `docker compose down -v && docker compose up -d --wait &&
  uv run irrevon init`, with an explicit warning that `down -v` deletes the
  disposable local volume.

## Verified non-findings

- The README command order, Python requirement, Node/Corepack split, two-phase
  migration bootstrap, loopback-only Docker binding, explicit demo migration
  authority, runtime app role, serve read role, seed-42 kept DSN, artifact
  handoff, Workbench build/staging, and alpha/synthetic limitations are
  internally consistent and executable.
- The hard-coded README demo DSN matches the generated default configuration;
  the demo also prints an equivalent evidence-specific DSN, so customized
  configurations retain a usable handoff.
- Public issue, private vulnerability, disabled Discussions, and stale site
  states are described honestly. No live provider, package publication,
  deployment, external setting, or public-history action was performed.
