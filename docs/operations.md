# Operations — running Irrevon as a service

Operator documentation for the self-hosted runtime (`irrevon worker` +
`irrevon serve`; ADR-0034, proposed). Scope honesty: this documents the
**continuous single-writer service** that exists and is tested. Multi-worker
operation is designed (ADR-0034 decision 2) and NOT available; nothing here
claims high availability.

## Deployment shape

Two long-lived processes against one Postgres 17:

| Process | Role | Network |
|---|---|---|
| `irrevon worker` | The single writer: recovery on boot, continuous reconciliation, orphan sweeps, gauges | Outbound to configured destinations + Postgres only |
| `irrevon serve` | Read-only workbench/API surface | Loopback listener (127.0.0.1), GET/HEAD only |

Run under systemd or a container supervisor; `irrevon init` scaffolds the
compose file with the digest-pinned Postgres. Configuration is
`irrevon.toml` (validated, unknown keys fatal) + environment variables for
every secret — config carries **names**, never values; provider adapters
refuse to construct without their credential variable and refuse
non-sandbox/test key prefixes outright.

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
- **Restore runbook**: restore the database → start ONE worker → recovery
  replay adjudicates every DISPATCHED/AMBIGUOUS record against the
  destinations BEFORE accepting new work — destination read-back, not the
  backup, is the authority for what actually happened after the backup
  point. Effects dispatched after the restore point surface as findings
  (orphan sweep + audit), not silent loss. Never re-dispatch on belief.
- Test the restore path routinely (a restore that has never run is a plan,
  not a capability). The e2e crash suites (`tests/process/`,
  `tests/e2e/`) exercise the same replay mechanics the restore path uses.

## Incident containment

`deny_entries` (the gate's deny-list) contains an effect class/type/scope
during an incident: inserted rows deny at the gate with evidence; lifts are
explicit rows. Preserve evidence first; classes and severities per master
doc §12.4. Credential exposure = stop-and-rotate (master doc §9).

## Data classification, redaction, retention

Ledger rows carry metadata + digests, never raw payload bodies (RFC-002 §0
rule 5); upstream identifiers are digested-or-absent in logs; `inspect`
redacts stable-id values by default; the serve surface exposes evidence
digest-only until the redaction pipeline lands (Q2). Retention/deletion of
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
