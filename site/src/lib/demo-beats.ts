// The 12-beat One-Way Seat model. Beat ids and caption strings are the
// N3↔N4 contract; every rendered value below is READ from the synced
// recorded artifact (src/data/demo/, drift-gated against
// web/fixtures/canonical) — beats are presentation states over the 7
// recorded Irrevon-leg events (beats 1–2 unpack `registered`; beat 12
// compounds two events; beats 1/2/4/10 additionally cite the flagship
// inspect record). Nothing here invents a value; the anti-fabrication e2e
// asserts the rendered page against the same JSON.
import artifact from "../data/demo/demo-artifact.json";
import inspect from "../data/demo/flagship-inspect.json";
import provenance from "../data/demo/provenance.json";

const events = artifact.events;
const summary = artifact.summary;

export const effectId: string = events[0].effect_id as string;
export const effectShort = `${effectId.slice(0, 12)}…`;
export const seed: number = summary.seed;
export const engineCommit: string = (provenance.engine_commit as string).slice(0, 7);
export const adapterId: string = inspect.record.adapter_id;

const gateAllow = inspect.gate_decisions[0];
const gateDeny = inspect.gate_decisions[1];
interface DenyEvidence {
  evidence?: { blocking_executions?: { execution_id: number; receipt_ids: number[]; finding_ids: number[] }[] };
}
const denyDedup = gateDeny.checks.find((c) => c.check === "dedup") as DenyEvidence | undefined;
const blocking = (denyDedup?.evidence?.blocking_executions ?? [])[0];
const variantDigest: string = events[5].parameter_variant as string;
export const variantShort = `${variantDigest.slice(0, 13)}…${variantDigest.slice(-6)}`;

export const citeLabel = `cites: execution ${blocking?.execution_id} · receipt ${blocking?.receipt_ids?.[0]} · finding ${blocking?.finding_ids?.[0]} · variant ${variantDigest.slice(0, 13)}…`;

export interface Beat {
  id: string;
  n: number;
  title: string;
  caption: string;
  facts: { label: string; value: string }[];
}

export const beats: Beat[] = [
  {
    id: "beat-01",
    n: 1,
    title: "Stable identifiers.",
    caption: "Order id, invoice id, authorization id — business facts, never model output.",
    facts: [
      { label: "stable_ids", value: Object.keys(inspect.record.stable_ids).join(" · ") },
      { label: "effect_type", value: inspect.record.effect_type },
      { label: "scope", value: inspect.record.scope },
    ],
  },
  {
    id: "beat-02",
    n: 2,
    title: "One identity.",
    caption: "The facts hash to one effect id. Different wording later cannot make a different identity.",
    facts: [{ label: "effect_id", value: effectShort }],
  },
  {
    id: "beat-03",
    n: 3,
    title: "Persisted before anything is sent.",
    caption: "The intent is inscribed in the append-only ledger.",
    facts: [{ label: "lifecycle", value: events[0].lifecycle as string }],
  },
  {
    id: "beat-04",
    n: 4,
    title: "The gate checks, with evidence.",
    caption: "Authority, capability, dedup — each check recorded.",
    facts: [
      { label: "decision", value: `${gateAllow.outcome} · decision_id ${gateAllow.decision_id}` },
      {
        label: "checks",
        value: gateAllow.checks.map((c) => `${c.check} ${c.status}`).join(" · "),
      },
    ],
  },
  {
    id: "beat-05",
    n: 5,
    title: "The crossing.",
    caption: "Allowed once, the dispatch passes the boundary — and the pawl seats. CLICK.",
    facts: [{ label: "effect_id", value: `${(events[1].effect_id as string).slice(0, 12)}…` }],
  },
  {
    id: "beat-06",
    n: 6,
    title: "Seated.",
    caption: "The destination committed. One external effect exists — geometry now holds it.",
    facts: [{ label: "destination_effects", value: String(summary.irrevon_leg.destination_effects) }],
  },
  {
    id: "beat-07",
    n: 7,
    title: "The response never arrives.",
    caption: "Bytes went out; no recognized answer came back. Not failed — AMBIGUOUS, recorded.",
    facts: [
      { label: "fault", value: events[1].fault as string },
      { label: "lifecycle", value: events[1].lifecycle as string },
    ],
  },
  {
    id: "beat-08",
    n: 8,
    title: "The process is killed.",
    caption: "A real SIGKILL, mid-doubt. The ledger is the only memory that survives.",
    facts: [{ label: "exit_status", value: String(events[2].exit_status) }],
  },
  {
    id: "beat-09",
    n: 9,
    title: "Recovery asks the destination.",
    caption: "A new process replays the ledger and probes — a read, through the port.",
    facts: [
      { label: "scanned", value: String(events[3].recovery?.scanned) },
      { label: "adjudicated", value: String(events[3].recovery?.adjudicated) },
    ],
  },
  {
    id: "beat-10",
    n: 10,
    title: "Evidence returns. The effect does not.",
    caption: "The receipt crosses back through the port; the ball never moves.",
    facts: [
      {
        label: "probe",
        value: `${inspect.probes[0].probe_kind} · ${inspect.probes[0].result} · n_found ${inspect.probes[0].n_found}`,
      },
      { label: "still seated", value: String(summary.irrevon_leg.destination_effects) },
    ],
  },
  {
    id: "beat-11",
    n: 11,
    title: "Settled: confirmed unique.",
    caption: "The record closes under the double rule. Committed, exactly once.",
    facts: [
      { label: "lifecycle", value: events[4].lifecycle as string },
      { label: "classification", value: events[4].classification as string },
    ],
  },
  {
    id: "beat-12",
    n: 12,
    title: "A re-worded retry arrives — same identity. Refused, with citations.",
    caption: "Nothing crosses the boundary twice.",
    facts: [
      { label: "parameter_variant", value: variantShort },
      { label: "replayed", value: String(events[5].replayed) },
      {
        label: "gate",
        value: `${events[6].outcome} · deny_check ${events[6].deny_check} · decision_id ${events[6].decision_id}`,
      },
    ],
  },
];

export const b5Lane = [
  {
    event: events[7].event as string,
    detail: `transport_outcome ${events[7].transport_outcome}`,
    caption: "The same fault against a developmental file-journal B5 stand-in: the response is lost.",
  },
  {
    event: events[8].event as string,
    detail: "durable runtime restarts the workflow",
    caption: "The durable journal restarts the workflow — memory of the attempt, not of the effect.",
  },
  {
    event: events[9].event as string,
    detail: `retried ${(events[9].retried as string[])?.[0]}`,
    caption: "The retry carries the same operation id and idempotency key. The key is sent — and ignored.",
  },
  {
    event: events[10].event as string,
    detail: `destination_effects ${events[10].destination_effects}`,
    caption: "The C2 destination now holds two effects. The duplicate is created, not caught.",
  },
];

export const contrast = {
  irrevon: {
    destinationEffects: summary.irrevon_leg.destination_effects,
    duplicateRejected: summary.irrevon_leg.duplicate_rejected,
    reconciled: summary.irrevon_leg.reconciled,
  },
  b5: {
    destinationEffects: summary.b5_leg.destination_effects,
    duplicateCreated: summary.b5_leg.duplicate_created,
  },
  holds: summary.contrast_holds,
};
