---
title: "Operations — running Irrevon as a service"
description: "Operator documentation: deployment shape, probes, shutdown and upgrades, the ten operator questions, SLO guidance, backup/restore, incident containment."
sourcePath: "docs/operations.md"
sourceSha256: "79d89385897b9b81e0babf07ee4b1510e6299552168b32209c389ae1047f0105"
syncedAt: "2026-07-24"
section: "Governance"
renderTitle: false
---

# Operations — running Irrevon as a service

Evaluation and operator-design notes for the self-hosted runtime (`irrevon
worker` + `irrevon serve`; ADR-0034, proposed). The continuous worker and
loopback read process exist and are tested, but the repository does **not** yet
claim a supported production deployment: the worker lacks a durable
registration/dispatch ingress, and host processes can instantiate the engine
outside that ownership boundary. The topology decision, fresh-cluster restore,
catch-up, and supervisor evidence remain open in review-queue item 45.
Multi-worker operation is not available and high availability is not claimed.

## Deployment shape

Two long-lived processes against one Postgres 17:

| Process | Role | Network |
|---|---|---|
| `irrevon worker` | The single writer: recovery on boot, continuous reconciliation, orphan sweeps, gauges | Outbound to configured destinations + Postgres only |
| `irrevon serve` | Read-only workbench/API surface | Loopback listener (127.0.0.1), GET/HEAD only |

For evaluation, run under a process supervisor; `irrevon init` scaffolds a
loopback-only **local-development** Compose database using PostgreSQL trust
authentication. It is not a production database template. Configuration is
`irrevon.toml` (validated, unknown keys fatal) + environment variables for
every secret — config carries **names**, never values; provider adapters
refuse to construct without their credential variable and refuse
non-sandbox/test key prefixes outright.

## Runnable synthetic worker exercise

This source-only smoke exercise starts the deterministic C2 reference
destination and runs three real worker cycles. It makes no provider call and is
not production evidence. Complete the README quickstart first so PostgreSQL is
running and migrations are current.

Add the reference adapter to the generated `irrevon.toml`:

```toml
[adapters.refdest-c2]
kind = "refdest"
```

In terminal 1, start the loopback-only synthetic destination on a known port:

```bash
uv run python -m irrevon.adapters.refdest_server \
  --port 5181 --seed 11 --profile C2
```

Wait for `REFDEST READY 5181`. In terminal 2, run a bounded worker:

```bash
IRREVON_REFDEST_URL=http://127.0.0.1:5181 \
  uv run irrevon worker \
    --interval 1 \
    --sweep-interval 2 \
    --health-file .scratch/worker-health.json \
    --max-cycles 3

uv run python -m json.tool .scratch/worker-health.json
```

The worker emits `worker.started`, three `worker.cycle` events, and
`worker.completed`; the health document ends at cycle 3. With no queued intent,
the gauges remain empty—this proves process wiring, writer ownership, sweep
scheduling, structured events, and health freshness, not recovery efficacy.
Use the README's faulted demo for the end-to-end evidence path. Stop terminal 1
with Ctrl-C.

## Health, liveness, readiness

- **Worker liveness**: `--health-file /path/health.json` is rewritten every
  cycle with `{at, cycle, open_executions, ambiguous_executions,
  oldest_open_age_s, open_findings}`. Liveness probe = file mtime fresher
  than ~3× `--interval` (exec probe or sidecar stat). A wedged worker stops
  refreshing; restart it — recovery replay is re-entrant (RFC-002 §7.1).
- **Read-surface readiness**: `irrevon serve` prints a single-line JSON
  ready document; probe its `url` with GET.
- **Startup**: the worker refuses to start if another writer holds the
  advisory lock (exit non-zero, `engine_refused` event) — never run two.

## Shutdown and upgrades

SIGTERM → the worker stops claiming, finishes the current cycle (wire calls
are short; no transaction ever spans I/O), releases the lock, exits 0. Fit
the probe/termination grace to ≥ one cycle interval. Rolling upgrade =
stop worker → run `irrevon doctor` (validates config, identity self-test,
DB reachability, migrations, privileges) → start new version; migrations
are plain SQL, applied in lexical order with a hash journal that refuses
edited history (ADR-0022). The workbench/API envelope is additive-only
(`schema_version` discipline); benchmark contracts version by format string.

## The ten operator questions → where the answer lives

| Question | Surface |
|---|---|
| What irreversible action was intended? | `irrevon inspect <effect_id>` (contract summary; stable ids redacted by default, `--reveal` local) |
| Was it persisted? | lifecycle history in `inspect` — INTENDED→PERSISTED is atomic at registration |
| Was it authorized? | gate history in `inspect` (every decision row carries the ordered checks + inputs digests) |
| Was it dispatched? | attempts/receipts in `inspect`; open attempts = in flight or crashed mid-flight |
| What did the destination actually do? | status probes + findings in `inspect`; `worker.cycle` settles report per cycle |
| What evidence supports the state? | every settle cites probe/receipt ids; `inspect` integrity section recomputes the identity hash |
| Is a retry safe? | never manual: `dispatch` on settled = evidenced deny; redispatch only via `resolve(REDISPATCHED)` under confirmed absence + fresh authority |
| Which provider capability changed? | `irrevon bench conform` declared-vs-observed report (non-conformant = contract drift; stop benchmark/live use, update declaration + citations) |
| Which effects need intervention? | `open_findings` gauge + ESCALATED_HUMAN queue (workbench Findings view); ambiguous-stuck escalation ≤2 business days (master doc §12.4) |
| What is violating an SLO? | the `worker.cycle` gauges below vs your declared targets |

## SLO guidance (declare per deployment; nothing here is a product claim)

Reasonable starting definitions an operator declares and monitors from
`worker.cycle` events: **ambiguity resolution latency** (p99
`oldest_open_age_s` under normal destination availability), **sweep
freshness** (time since last `sweep_completed` per adapter), **escalation
budget** (no OPEN finding older than the §12.4 budget), **worker liveness**
(health-file freshness). Alert on ERROR-severity events
(`worker.reconcile_error`, `worker.sweep_error`, `engine_refused`) — ERROR
means Irrevon malfunctioning; WARN means the system working and finding
something (RFC-002 §11).

## Backup, restore, disaster recovery

The ledger is the ONLY durable state (logs are diagnostics; never replayed).
Standard Postgres discipline applies, with one Irrevon-specific rule:

- Continuous archiving + PITR (`pg_basebackup` + WAL archiving) is the
  recommended shape; nightly `pg_dump` is the floor.
- **Candidate restore sequence (not yet a production capability):** restore the
  database → keep registration and dispatch ingress stopped → start one worker
  → inspect recovery and sweep evidence against each destination. Destination
  read-back, not the backup, is authoritative after the backup point. The
  current code does not yet prove that a fresh-cluster restore discovers every
  post-backup effect, so operators must not infer complete catch-up.
- Test the restore path routinely (a restore that has never run is a plan,
  not a capability). The e2e crash suites (`tests/process/`,
  `tests/e2e/`) exercise the same replay mechanics the restore path uses.

## Incident containment

`deny_entries` (the gate's deny-list) contains an effect class/type/scope
during an incident: inserted rows deny at the gate with evidence; lifts are
explicit rows. Preserve evidence first; classes and severities per master
doc §12.4. Credential exposure = stop-and-rotate (master doc §9).

## Data classification, redaction, retention

Ledger rows include validated dispatch parameters needed to reproduce an
authorized request, plus digests; they do not retain raw provider response
bodies. Treat the database as sensitive. Upstream identifiers are
digested-or-absent in structured logs; `inspect` redacts stable-id values by
default, and the serve surface returns digested stable identifiers. Explicit
local `inspect --reveal` may show raw stable identifiers to an authorized local
operator. Retention/deletion of
ledger history is the operator's policy — rows are append-only by role
design; deletion is a DBA act on a copy-and-truncate basis, never in-place
mutation of live history.
## Compatibility, versioning, and deprecation

- **Package/API**: pre-release (`0.x`); no compatibility guarantee is claimed
  before the first tagged release (release mechanics are human-gated,
  ADR-0018). From the first release: semantic versioning; any
  guarantee-affecting change is MINOR+ with an ADR (master doc §12.3).
- **Wire/JSON surfaces**: the serve envelope and CLI `--json` documents are
  additive-only under a `schema_version` member; benchmark artifacts version
  by format string (`irrevonbench/<kind>/v1`) — a shape change is a new
  format version plus an ADR, and old readers must reject unknown formats
  rather than guess (enforced in `irrevon.bench.formats`).
- **Database**: migrations are append-only plain SQL with a content-hash
  journal that refuses edited history (ADR-0022); downgrade is
  restore-from-backup, never reverse migration.
- **Deprecation policy**: a deprecated surface keeps working for at least one
  MINOR release with a WARN-severity structured event naming the
  replacement; removal requires a changelog entry and, when
  guarantee-affecting, an ADR. Benchmark formats are never deprecated
  in-place post-freeze — frozen artifacts stay readable forever
  (append-only result store, preregistration §8).
