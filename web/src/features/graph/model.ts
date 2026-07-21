import type { EffectRecord } from "@/shared/contracts/generated/effect-record";
import type { InspectPayload } from "@/shared/api/types";

/**
 * Pure causal-graph model builder (REDESIGN-BRIEF §4, graph-semantics §1).
 * Every node maps to an exact source record/field or a labeled absence;
 * every edge carries `from`, `to`, `relation`, and an `evidencePath` that
 * resolves inside the builder's input. No DOM measurement, no randomness:
 * byte-stable input ⇒ byte-stable output. Unsupported relationships are
 * omitted, never drawn faintly.
 */

export type NodeKind =
  | "intent"
  | "identity"
  | "execution"
  | "gate"
  | "attempt"
  | "probe"
  | "observation"
  | "unknown-slot"
  | "absence"
  | "finding"
  | "resolution"
  | "adapter"
  | "authority"
  | "variant";

export const RELATIONS = [
  "registered-as",
  "declares-destination",
  "declared-as",
  "authorized-by",
  "opened",
  "allowed-by",
  "denied-by",
  "dedup-cites",
  "variant-of",
  "dispatched-through",
  "externalized-to",
  "evidence-gap",
  "observed-as",
  "reconciled-as",
  "produced-finding",
  "resolved-through",
  "recovered-after-crash",
] as const;

export type Relation = (typeof RELATIONS)[number];

export type EdgeStroke = "solid" | "dashed" | "interrupted";

export type NodeSize = "standard" | "gate" | "compact";

export interface GraphFact {
  label: string;
  value: string;
  /** Path into the builder input that carries this fact. */
  path: string;
}

export interface GraphNode {
  /** Stable id: node:<kind>:<source-id> — keys selection and URL state. */
  id: string;
  kind: NodeKind;
  /** 11px uppercase kind label. */
  kindLabel: string;
  /** Exact primary value/ID (truncated only at render per the contract). */
  primary: string;
  /** Explicit absence/unknown wording, rendered as text on the node. */
  absenceText?: string;
  /** Unrecognized enum encountered — labeled verbatim, never coerced. */
  unrecognized?: boolean;
  /** Destination-side (probe/receipt-mediated) — hatched fill. */
  hatched?: boolean;
  /** Dashed void frame (explicit absence) or dashed declared border. */
  frame: "solid" | "dashed" | "void";
  /** Native status to render, when this source owns one. */
  status?: {
    channel: "lifecycle" | "classification" | "resolution" | "transport";
    value: string;
  };
  size: NodeSize;
  /** Contract citation for the node itself. */
  sourcePath: string;
  facts: GraphFact[];
  /** Causal rank (column); laterals share their anchor's rank. */
  rank: number;
  /** true = lateral lane (denies, variants, probes), below the main flow. */
  lateral: boolean;
  /** Deterministic ordering key within (rank, lateral): (created_at, id). */
  orderKey: string;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  relation: Relation;
  stroke: EdgeStroke;
  evidencePath: string;
}

export interface GraphAnnotation {
  id: string;
  kind: "notch" | "crash-seam";
  /** Drawn at the boundary BEFORE this rank. */
  beforeRank: number;
  label: string;
  epistemic?: "EI";
  sourcePath: string;
}

export interface GraphModel {
  effectId: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  annotations: GraphAnnotation[];
  /** integrity.matches === false ⇒ blocking incident banner. */
  integrityFailure: boolean;
  notes: string[];
}

export interface BuildInput {
  inspect: InspectPayload;
  record?: EffectRecord;
}

const KIND_LABELS: Record<NodeKind, string> = {
  intent: "Intent",
  identity: "Effect identity",
  execution: "Execution",
  gate: "Gate decision",
  attempt: "Dispatch attempt",
  probe: "Probe",
  observation: "Destination observation",
  "unknown-slot": "Labeled unknown",
  absence: "Explicit absence",
  finding: "Finding",
  resolution: "Resolution chain",
  adapter: "Adapter",
  authority: "Authority",
  variant: "Parameter variant",
};

const RANK = {
  intent: 0,
  identity: 1,
  execution: 2,
  gate: 3,
  attempt: 4,
  probe: 5,
  observation: 6,
  finding: 7,
  resolution: 8,
} as const;

const KNOWN_LIFECYCLES: readonly string[] = [
  "INTENDED",
  "PERSISTED",
  "CANCELLED",
  "DISPATCHED",
  "SETTLED_COMMITTED",
  "SETTLED_FAILED",
  "AMBIGUOUS",
];
const KNOWN_OUTCOMES: readonly string[] = ["OK", "FAILED", "TIMEOUT", "LOST"];

/** Resolve a builder-emitted path (e.g. `inspect.timeline[2].evidence.attempt_id`). */
export function resolveEvidencePath(input: BuildInput, path: string): unknown {
  const segments = path.replaceAll("]", "").split(/[.[]/);
  let cursor: unknown = input;
  for (const segment of segments) {
    if (cursor === null || cursor === undefined || typeof cursor !== "object") return undefined;
    cursor = (cursor as Record<string, unknown>)[segment];
  }
  return cursor;
}

export function buildEffectGraph(input: BuildInput): GraphModel {
  const { inspect, record } = input;
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const annotations: GraphAnnotation[] = [];
  const notes: string[] = [];

  const effectId = inspect.record.effect_id;
  const nid = (kind: string, sourceId: string | number) => `node:${kind}:${String(sourceId)}`;

  const intentId = nid("intent", effectId);
  const identityId = nid("identity", effectId);

  // ── Intent ────────────────────────────────────────────────────────────
  const stableIdKeys = Object.keys(inspect.record.stable_ids).sort();
  nodes.push({
    id: intentId,
    kind: "intent",
    kindLabel: KIND_LABELS.intent,
    primary: `${inspect.record.effect_type} · ${inspect.record.scope}`,
    frame: "solid",
    size: "standard",
    sourcePath: "inspect.record.effect_type",
    facts: [
      {
        label: "effect_type",
        value: inspect.record.effect_type,
        path: "inspect.record.effect_type",
      },
      {
        label: "effect_class",
        value: inspect.record.effect_class,
        path: "inspect.record.effect_class",
      },
      { label: "scope", value: inspect.record.scope, path: "inspect.record.scope" },
      {
        label: "stable_ids (keys)",
        value: stableIdKeys.join(", "),
        path: "inspect.record.stable_ids",
      },
    ],
    rank: RANK.intent,
    lateral: false,
    orderKey: `0:${effectId}`,
  });

  // ── Effect identity ───────────────────────────────────────────────────
  const lifecycleKnown = KNOWN_LIFECYCLES.includes(inspect.record.lifecycle);
  nodes.push({
    id: identityId,
    kind: "identity",
    kindLabel: KIND_LABELS.identity,
    primary: effectId,
    frame: "solid",
    size: "standard",
    ...(lifecycleKnown ? {} : { unrecognized: true }),
    status: { channel: "lifecycle", value: inspect.record.lifecycle },
    sourcePath: "inspect.record.effect_id",
    facts: [
      { label: "effect_id", value: effectId, path: "inspect.record.effect_id" },
      {
        label: "integrity.matches",
        value: String(inspect.integrity.matches),
        path: "inspect.integrity.matches",
      },
      {
        label: "recomputed_intent_id",
        value: inspect.integrity.recomputed_intent_id,
        path: "inspect.integrity.recomputed_intent_id",
      },
    ],
    rank: RANK.identity,
    lateral: false,
    orderKey: `0:${effectId}`,
  });
  edges.push({
    id: `edge:registered-as:${effectId}`,
    from: intentId,
    to: identityId,
    relation: "registered-as",
    stroke: "solid",
    evidencePath: "inspect.record.effect_id",
  });

  // ── Adapter flank (declared destination) ──────────────────────────────
  const adapterId = nid("adapter", inspect.record.adapter_id);
  nodes.push({
    id: adapterId,
    kind: "adapter",
    kindLabel: KIND_LABELS.adapter,
    primary: inspect.record.adapter_id,
    frame: "dashed",
    size: "compact",
    sourcePath: "inspect.record.adapter_id",
    facts: [
      {
        label: "adapter_id",
        value: inspect.record.adapter_id,
        path: "inspect.record.adapter_id",
      },
    ],
    rank: RANK.intent,
    lateral: true,
    orderKey: `1:${inspect.record.adapter_id}`,
  });
  edges.push({
    id: `edge:declares-destination:${inspect.record.adapter_id}`,
    from: intentId,
    to: adapterId,
    relation: "declares-destination",
    stroke: "solid",
    evidencePath: "inspect.record.adapter_id",
  });

  // ── Authority (Q1 record only — evidence carrier, ADR-0019) ───────────
  if (record?.authority_ref !== undefined) {
    const authorityId = nid("authority", record.authority_ref);
    nodes.push({
      id: authorityId,
      kind: "authority",
      kindLabel: KIND_LABELS.authority,
      primary: record.authority_ref,
      frame: "dashed",
      size: "compact",
      sourcePath: "record.authority_ref",
      facts: [
        { label: "authority_ref", value: record.authority_ref, path: "record.authority_ref" },
        { label: "stamped_at", value: record.stamped_at, path: "record.stamped_at" },
      ],
      rank: RANK.intent,
      lateral: true,
      orderKey: `0:${record.authority_ref}`,
    });
    edges.push({
      id: `edge:authorized-by:${record.authority_ref}`,
      from: intentId,
      to: authorityId,
      relation: "authorized-by",
      stroke: "dashed",
      evidencePath: "record.authority_ref",
    });
  }

  // ── Executions (timeline grouped by operation_id) ─────────────────────
  const timeline = [...inspect.timeline].sort((a, b) => a.transition_seq - b.transition_seq);
  if (timeline.length === 0) {
    notes.push("no transitions recorded");
  }
  const executions = new Map<string, { step: number; genesisIdx: number }>();
  timeline.forEach((transition, index) => {
    if (!executions.has(transition.operation_id)) {
      executions.set(transition.operation_id, { step: transition.step, genesisIdx: index });
    }
  });
  const executionIds = new Map<string, string>();
  for (const [operationId, info] of [...executions.entries()].sort(
    (a, b) => a[1].step - b[1].step,
  )) {
    const id = nid("execution", operationId);
    executionIds.set(operationId, id);
    const genesis = timeline[info.genesisIdx];
    const openedBy =
      genesis && typeof genesis.evidence.opened_by === "string"
        ? genesis.evidence.opened_by
        : (genesis?.cause ?? "unknown");
    const idxOf = (seq: number) => inspect.timeline.findIndex((t) => t.transition_seq === seq);
    const genesisPath = genesis
      ? `inspect.timeline[${idxOf(genesis.transition_seq)}]`
      : "inspect.timeline";
    nodes.push({
      id,
      kind: "execution",
      kindLabel: KIND_LABELS.execution,
      primary: `step ${info.step}`,
      frame: "solid",
      size: "standard",
      sourcePath: `${genesisPath}.operation_id`,
      facts: [
        { label: "operation_id", value: operationId, path: `${genesisPath}.operation_id` },
        { label: "opened_by", value: openedBy, path: `${genesisPath}.cause` },
        {
          label: "transitions",
          value: String(timeline.filter((t) => t.operation_id === operationId).length),
          path: "inspect.timeline",
        },
      ],
      rank: RANK.execution,
      lateral: false,
      orderKey: `${String(info.step).padStart(6, "0")}:${operationId}`,
    });
    edges.push({
      id: `edge:opened:${operationId}`,
      from: identityId,
      to: id,
      relation: "opened",
      stroke: "solid",
      evidencePath: `${genesisPath}.cause`,
    });
  }

  // ── Gate decisions ────────────────────────────────────────────────────
  const decisions = [...inspect.gate_decisions].sort((a, b) => a.decision_id - b.decision_id);
  const decisionNodeIds = new Map<number, string>();
  decisions.forEach((decision) => {
    const idxInPayload = inspect.gate_decisions.findIndex(
      (d) => d.decision_id === decision.decision_id,
    );
    const base = `inspect.gate_decisions[${idxInPayload}]`;
    const isDeny = decision.outcome === "DENY";
    const unknownOutcome = decision.outcome !== "ALLOW" && decision.outcome !== "DENY";
    const id = nid("gate", decision.decision_id);
    decisionNodeIds.set(decision.decision_id, id);
    nodes.push({
      id,
      kind: "gate",
      kindLabel: KIND_LABELS.gate,
      primary: unknownOutcome
        ? `${decision.outcome} (unrecognized value)`
        : isDeny
          ? `DENY ⊘ ${decision.deny_check ?? ""}`.trim()
          : "ALLOW",
      frame: "solid",
      size: "gate",
      ...(unknownOutcome ? { unrecognized: true } : {}),
      sourcePath: `${base}.outcome`,
      facts: [
        {
          label: "decision_id",
          value: String(decision.decision_id),
          path: `${base}.decision_id`,
        },
        { label: "variant", value: decision.variant, path: `${base}.variant` },
        { label: "outcome", value: decision.outcome, path: `${base}.outcome` },
        ...(decision.deny_check !== null
          ? [{ label: "deny_check", value: decision.deny_check, path: `${base}.deny_check` }]
          : []),
        {
          label: "checks",
          value: decision.checks.map((c) => `${c.check}:${c.status}`).join(", "),
          path: `${base}.checks`,
        },
      ],
      rank: RANK.gate,
      lateral: isDeny,
      orderKey: `${decision.created_at}:${String(decision.decision_id).padStart(6, "0")}`,
    });

    if (isDeny) {
      // The denied dispatch request flows from the identity; nothing crosses
      // the notch on this path.
      edges.push({
        id: `edge:denied-by:${decision.decision_id}`,
        from: identityId,
        to: id,
        relation: "denied-by",
        stroke: "solid",
        evidencePath: `${base}.outcome`,
      });
      const blocking = decision.evidence.blocking_executions ?? [];
      blocking.forEach((blocked, blockedIdx) => {
        const target = executionIds.get(blocked.operation_id);
        if (target) {
          edges.push({
            id: `edge:dedup-cites:${decision.decision_id}:${blocked.operation_id}`,
            from: id,
            to: target,
            relation: "dedup-cites",
            stroke: "solid",
            evidencePath: `${base}.evidence.blocking_executions[${blockedIdx}].operation_id`,
          });
        }
      });
      const variants = decision.evidence.parameter_variants ?? [];
      variants.forEach((digest, variantIdx) => {
        const variantId = nid("variant", digest);
        if (!nodes.some((n) => n.id === variantId)) {
          nodes.push({
            id: variantId,
            kind: "variant",
            kindLabel: KIND_LABELS.variant,
            primary: digest,
            frame: "dashed",
            size: "compact",
            sourcePath: `${base}.evidence.parameter_variants[${variantIdx}]`,
            facts: [
              {
                label: "parameter_variant",
                value: digest,
                path: `${base}.evidence.parameter_variants[${variantIdx}]`,
              },
            ],
            rank: RANK.identity,
            lateral: true,
            orderKey: `${decision.created_at}:${digest}`,
          });
          edges.push({
            id: `edge:variant-of:${digest}`,
            from: variantId,
            to: identityId,
            relation: "variant-of",
            stroke: "dashed",
            evidencePath: `${base}.evidence.parameter_variants[${variantIdx}]`,
          });
        }
      });
    }
  });

  // allowed-by: the gate_allow transition cites its decision_id.
  timeline.forEach((transition) => {
    if (transition.cause !== "gate_allow") return;
    const decisionId = transition.evidence.decision_id;
    if (typeof decisionId !== "number") return;
    const gateNode = decisionNodeIds.get(decisionId);
    const executionNode = executionIds.get(transition.operation_id);
    const idx = inspect.timeline.findIndex(
      (t) => t.transition_seq === transition.transition_seq,
    );
    if (gateNode && executionNode) {
      edges.push({
        id: `edge:allowed-by:${transition.transition_seq}`,
        from: executionNode,
        to: gateNode,
        relation: "allowed-by",
        stroke: "solid",
        evidencePath: `inspect.timeline[${idx}].evidence.decision_id`,
      });
    }
  });

  // ── The irreversible boundary (one notch, at the first gate_allow) ────
  const dispatched = timeline.some(
    (t) => t.cause === "gate_allow" && t.to_state === "DISPATCHED",
  );
  if (dispatched) {
    const idx = inspect.timeline.findIndex(
      (t) => t.cause === "gate_allow" && t.to_state === "DISPATCHED",
    );
    annotations.push({
      id: "annotation:notch",
      kind: "notch",
      beforeRank: RANK.attempt,
      label: "externalized — reconcile or compensate only (ADR-007)",
      sourcePath: `inspect.timeline[${idx}].cause`,
    });
  }

  // ── Crash/restart seam (inferred from the recovery actor — [EI]) ──────
  const recoveryIdx = inspect.timeline.findIndex((t) => t.actor === "recovery");
  if (recoveryIdx !== -1) {
    annotations.push({
      id: "annotation:crash-seam",
      kind: "crash-seam",
      beforeRank: RANK.probe,
      label: "recovery actor ⇒ a restart preceded this event",
      epistemic: "EI",
      sourcePath: `inspect.timeline[${recoveryIdx}].actor`,
    });
  }

  // ── Dispatch attempts (receipts) ──────────────────────────────────────
  const receipts = [...inspect.receipts].sort((a, b) => a.receipt_id - b.receipt_id);
  const attemptIds = new Map<number, string>();
  receipts.forEach((receipt) => {
    const idx = inspect.receipts.findIndex((r) => r.receipt_id === receipt.receipt_id);
    const base = `inspect.receipts[${idx}]`;
    const id = nid("attempt", receipt.receipt_id);
    attemptIds.set(receipt.receipt_id, id);
    const unknownOutcome = !KNOWN_OUTCOMES.includes(receipt.transport_outcome);
    nodes.push({
      id,
      kind: "attempt",
      kindLabel: KIND_LABELS.attempt,
      primary: `attempt ${receipt.attempt_no} (${receipt.kind})`,
      frame: "solid",
      size: "standard",
      ...(unknownOutcome ? { unrecognized: true } : {}),
      status: { channel: "transport", value: receipt.transport_outcome },
      sourcePath: `${base}.receipt_id`,
      facts: [
        { label: "receipt_id", value: String(receipt.receipt_id), path: `${base}.receipt_id` },
        { label: "kind", value: receipt.kind, path: `${base}.kind` },
        {
          label: "idempotency_key",
          value: receipt.idempotency_key,
          path: `${base}.idempotency_key`,
        },
        {
          label: "transport_outcome",
          value: receipt.transport_outcome,
          path: `${base}.transport_outcome`,
        },
        ...(receipt.failure_kind !== null
          ? [
              {
                label: "failure_kind",
                value: receipt.failure_kind,
                path: `${base}.failure_kind`,
              },
            ]
          : []),
        { label: "recorded_by", value: receipt.recorded_by, path: `${base}.recorded_by` },
      ],
      rank: RANK.attempt,
      lateral: false,
      orderKey: `${receipt.recorded_at}:${String(receipt.receipt_id).padStart(6, "0")}`,
    });
    // dispatched-through: gate ALLOW → attempt, crossing the notch.
    const allowTransition = timeline.find(
      (t) =>
        t.operation_id === receipt.operation_id &&
        t.cause === "gate_allow" &&
        typeof t.evidence.decision_id === "number",
    );
    const gateNode = allowTransition
      ? decisionNodeIds.get(allowTransition.evidence.decision_id as number)
      : undefined;
    edges.push({
      id: `edge:dispatched-through:${receipt.receipt_id}`,
      from: gateNode ?? executionIds.get(receipt.operation_id) ?? identityId,
      to: id,
      relation: "dispatched-through",
      stroke: "solid",
      evidencePath: `${base}.operation_id`,
    });
  });

  // ── Destination side: observations, unknowns, absences ────────────────
  const probes = [...inspect.probes].sort((a, b) => a.probe_id - b.probe_id);
  const probeIds = new Map<number, string>();
  probes.forEach((probe) => {
    const idx = inspect.probes.findIndex((p) => p.probe_id === probe.probe_id);
    const base = `inspect.probes[${idx}]`;
    const id = nid("probe", probe.probe_id);
    probeIds.set(probe.probe_id, id);
    const known = ["PRESENT", "ABSENT", "INDETERMINATE"].includes(String(probe.result));
    nodes.push({
      id,
      kind: "probe",
      kindLabel: KIND_LABELS.probe,
      primary: `${probe.probe_kind} → ${probe.result}${probe.n_found !== null ? ` (n=${probe.n_found})` : ""}`,
      frame: "solid",
      hatched: true,
      size: "compact",
      ...(known ? {} : { unrecognized: true }),
      sourcePath: `${base}.probe_id`,
      facts: [
        { label: "probe_id", value: String(probe.probe_id), path: `${base}.probe_id` },
        { label: "probe_kind", value: probe.probe_kind, path: `${base}.probe_kind` },
        { label: "result", value: String(probe.result), path: `${base}.result` },
        ...(probe.n_found !== null
          ? [{ label: "n_found", value: String(probe.n_found), path: `${base}.n_found` }]
          : []),
        { label: "queried_at", value: probe.queried_at, path: `${base}.queried_at` },
      ],
      rank: RANK.probe,
      lateral: true,
      orderKey: `${probe.queried_at}:${String(probe.probe_id).padStart(6, "0")}`,
    });
  });

  // Observation node: a destination_ref recorded by a receipt or finding.
  const findings = [...inspect.findings].sort((a, b) => a.finding_id - b.finding_id);
  const destinationRefs: { ref: string; path: string; orderKey: string }[] = [];
  receipts.forEach((receipt) => {
    if (receipt.destination_ref !== null && receipt.transport_outcome === "OK") {
      const idx = inspect.receipts.findIndex((r) => r.receipt_id === receipt.receipt_id);
      destinationRefs.push({
        ref: receipt.destination_ref,
        path: `inspect.receipts[${idx}].destination_ref`,
        orderKey: receipt.recorded_at,
      });
    }
  });
  findings.forEach((finding) => {
    if (finding.destination_ref !== null) {
      const idx = inspect.findings.findIndex((f) => f.finding_id === finding.finding_id);
      destinationRefs.push({
        ref: finding.destination_ref,
        path: `inspect.findings[${idx}].destination_ref`,
        orderKey: finding.created_at,
      });
    }
  });
  const seenRefs = new Set<string>();
  const observationIds = new Map<string, string>();
  for (const { ref, path, orderKey } of destinationRefs) {
    if (seenRefs.has(ref)) continue;
    seenRefs.add(ref);
    const id = nid("observation", ref);
    observationIds.set(ref, id);
    nodes.push({
      id,
      kind: "observation",
      kindLabel: KIND_LABELS.observation,
      primary: ref,
      frame: "solid",
      hatched: true,
      size: "standard",
      sourcePath: path,
      facts: [{ label: "destination_ref", value: ref, path }],
      rank: RANK.observation,
      lateral: false,
      orderKey: `${orderKey}:${ref}`,
    });
  }

  // externalized-to: OK receipt with a destination_ref.
  receipts.forEach((receipt) => {
    if (receipt.transport_outcome === "OK" && receipt.destination_ref !== null) {
      const idx = inspect.receipts.findIndex((r) => r.receipt_id === receipt.receipt_id);
      const target = observationIds.get(receipt.destination_ref);
      const from = attemptIds.get(receipt.receipt_id);
      if (target && from) {
        edges.push({
          id: `edge:externalized-to:${receipt.receipt_id}`,
          from,
          to: target,
          relation: "externalized-to",
          stroke: "solid",
          evidencePath: `inspect.receipts[${idx}].destination_ref`,
        });
      }
    }
  });

  // Absence: two-plus ABSENT probes confirm the destination slot is empty.
  const absentProbes = probes.filter((p) => String(p.result) === "ABSENT" && p.n_found === 0);
  let absenceNodeId: string | null = null;
  if (absentProbes.length > 0) {
    absenceNodeId = nid("absence", effectId);
    nodes.push({
      id: absenceNodeId,
      kind: "absence",
      kindLabel: KIND_LABELS.absence,
      primary: `confirmed absent — ${absentProbes.length} probe${absentProbes.length === 1 ? "" : "s"}`,
      absenceText: "no destination effect exists for this dispatch",
      frame: "void",
      size: "standard",
      sourcePath: `inspect.probes[${inspect.probes.findIndex((p) => p.probe_id === absentProbes[0]?.probe_id)}].result`,
      facts: absentProbes.map((p) => ({
        label: `probe ${p.probe_id}`,
        value: `${String(p.result)} (n_found=${String(p.n_found)})`,
        path: `inspect.probes[${inspect.probes.findIndex((x) => x.probe_id === p.probe_id)}].result`,
      })),
      rank: RANK.observation,
      lateral: false,
      orderKey: `${absentProbes[0]?.queried_at ?? ""}:absence`,
    });
  }

  // Labeled unknown: AMBIGUOUS frontier with no settling probe.
  let unknownSlotId: string | null = null;
  if (inspect.record.lifecycle === "AMBIGUOUS") {
    unknownSlotId = nid("unknown-slot", effectId);
    nodes.push({
      id: unknownSlotId,
      kind: "unknown-slot",
      kindLabel: KIND_LABELS["unknown-slot"],
      primary: "?",
      absenceText: "destination state unknown — awaiting reconciliation",
      frame: "dashed",
      hatched: true,
      size: "standard",
      sourcePath: "inspect.record.lifecycle",
      facts: [
        {
          label: "lifecycle",
          value: inspect.record.lifecycle,
          path: "inspect.record.lifecycle",
        },
      ],
      rank: RANK.observation,
      lateral: false,
      orderKey: "zzz:unknown",
    });
  }

  // evidence-gap: LOST/TIMEOUT attempt → the unknown/absence slot. The
  // interrupted stroke is never repaired; probes tell the rest.
  receipts.forEach((receipt) => {
    if (receipt.transport_outcome === "LOST" || receipt.transport_outcome === "TIMEOUT") {
      const idx = inspect.receipts.findIndex((r) => r.receipt_id === receipt.receipt_id);
      const from = attemptIds.get(receipt.receipt_id);
      const target =
        unknownSlotId ??
        absenceNodeId ??
        // Settled after doubt: the observation the probes later confirmed.
        [...observationIds.values()][0] ??
        null;
      if (from && target !== null) {
        edges.push({
          id: `edge:evidence-gap:${receipt.receipt_id}`,
          from,
          to: target,
          relation: "evidence-gap",
          stroke: "interrupted",
          evidencePath: `inspect.receipts[${idx}].transport_outcome`,
        });
      }
    }
  });

  // observed-as: probe → observation/absence.
  probes.forEach((probe) => {
    const idx = inspect.probes.findIndex((p) => p.probe_id === probe.probe_id);
    const from = probeIds.get(probe.probe_id);
    if (!from) return;
    let target: string | null = null;
    if (String(probe.result) === "PRESENT") {
      target = [...observationIds.values()][0] ?? null;
    } else if (String(probe.result) === "ABSENT") {
      target = absenceNodeId;
    }
    if (target !== null) {
      edges.push({
        id: `edge:observed-as:${probe.probe_id}`,
        from,
        to: target,
        relation: "observed-as",
        stroke: "solid",
        evidencePath: `inspect.probes[${idx}].result`,
      });
    }
  });

  // reconciled-as: a settle transition citing probe_ids.
  timeline.forEach((transition) => {
    const probeIdList = transition.evidence.probe_ids;
    if (!Array.isArray(probeIdList) || probeIdList.length === 0) return;
    const idx = inspect.timeline.findIndex(
      (t) => t.transition_seq === transition.transition_seq,
    );
    const executionNode = executionIds.get(transition.operation_id);
    if (!executionNode) return;
    for (const probeId of probeIdList) {
      const from = typeof probeId === "number" ? probeIds.get(probeId) : undefined;
      if (from) {
        edges.push({
          id: `edge:reconciled-as:${transition.transition_seq}:${String(probeId)}`,
          from,
          to: executionNode,
          relation: "reconciled-as",
          stroke: "solid",
          evidencePath: `inspect.timeline[${idx}].evidence.probe_ids`,
        });
      }
    }
  });

  // ── Findings and the resolution chain ─────────────────────────────────
  const resolutions = [...inspect.resolutions].sort(
    (a, b) => a.resolution_seq - b.resolution_seq,
  );
  findings.forEach((finding) => {
    const idx = inspect.findings.findIndex((f) => f.finding_id === finding.finding_id);
    const base = `inspect.findings[${idx}]`;
    const id = nid("finding", finding.finding_id);
    const knownClassification = [
      "CONFIRMED_UNIQUE",
      "DUPLICATE",
      "LOST",
      "ORPHANED",
      "CONTRADICTED",
    ].includes(String(finding.classification));
    nodes.push({
      id,
      kind: "finding",
      kindLabel: KIND_LABELS.finding,
      primary: String(finding.classification),
      frame: "solid",
      size: "standard",
      ...(knownClassification ? {} : { unrecognized: true }),
      status: { channel: "classification", value: String(finding.classification) },
      sourcePath: `${base}.finding_id`,
      facts: [
        { label: "finding_id", value: String(finding.finding_id), path: `${base}.finding_id` },
        {
          label: "classification",
          value: String(finding.classification),
          path: `${base}.classification`,
        },
        ...(finding.excess_effect_count !== null
          ? [
              {
                label: "excess_effect_count",
                value: String(finding.excess_effect_count),
                path: `${base}.excess_effect_count`,
              },
            ]
          : []),
        {
          label: "evidence_digest",
          value: finding.evidence_digest,
          path: `${base}.evidence_digest`,
        },
        { label: "created_by", value: finding.created_by, path: `${base}.created_by` },
      ],
      rank: RANK.finding,
      lateral: false,
      orderKey: `${finding.created_at}:${String(finding.finding_id).padStart(6, "0")}`,
    });

    // produced-finding: cited probes when present, else the owning execution.
    const probeIdList = finding.evidence.probe_ids;
    if (Array.isArray(probeIdList) && probeIdList.length > 0) {
      for (const probeId of probeIdList) {
        const from = typeof probeId === "number" ? probeIds.get(probeId) : undefined;
        if (from) {
          edges.push({
            id: `edge:produced-finding:${finding.finding_id}:${String(probeId)}`,
            from,
            to: id,
            relation: "produced-finding",
            stroke: "solid",
            evidencePath: `${base}.evidence.probe_ids`,
          });
        }
      }
    } else {
      const owner = [...executionIds.values()][0];
      if (owner) {
        edges.push({
          id: `edge:produced-finding:${finding.finding_id}`,
          from: owner,
          to: id,
          relation: "produced-finding",
          stroke: "solid",
          evidencePath: `${base}.finding_id`,
        });
      }
    }

    // DUPLICATE: the observed excess is destination-side evidence with no
    // ledger attempt — an explicitly labeled hatched node.
    if (
      String(finding.classification) === "DUPLICATE" &&
      finding.excess_effect_count !== null
    ) {
      const excessId = nid("observation", `excess-${finding.finding_id}`);
      nodes.push({
        id: excessId,
        kind: "observation",
        kindLabel: KIND_LABELS.observation,
        primary: `observed excess ×${finding.excess_effect_count}`,
        absenceText: "observed excess — no ledger attempt",
        frame: "dashed",
        hatched: true,
        size: "standard",
        sourcePath: `${base}.excess_effect_count`,
        facts: [
          {
            label: "excess_effect_count",
            value: String(finding.excess_effect_count),
            path: `${base}.excess_effect_count`,
          },
        ],
        rank: RANK.observation,
        lateral: false,
        orderKey: `${finding.created_at}:excess`,
      });
      const auditProbe = probes.find((p) => (p.n_found ?? 0) >= 2);
      if (auditProbe) {
        const from = probeIds.get(auditProbe.probe_id);
        const probeIdx = inspect.probes.findIndex((p) => p.probe_id === auditProbe.probe_id);
        if (from) {
          edges.push({
            id: `edge:observed-as:excess:${finding.finding_id}`,
            from,
            to: excessId,
            relation: "observed-as",
            stroke: "solid",
            evidencePath: `inspect.probes[${probeIdx}].n_found`,
          });
        }
      }
    }

    // resolved-through: one resolution-chain node per finding with steps.
    const chain = resolutions.filter((r) => r.finding_id === finding.finding_id);
    if (chain.length > 0) {
      const last = chain[chain.length - 1];
      const resolutionId = nid("resolution", finding.finding_id);
      const lastIdx = inspect.resolutions.findIndex(
        (r) => r.resolution_seq === last?.resolution_seq,
      );
      nodes.push({
        id: resolutionId,
        kind: "resolution",
        kindLabel: KIND_LABELS.resolution,
        primary: String(last?.to_status ?? "UNKNOWN"),
        frame: "solid",
        size: "standard",
        status: { channel: "resolution", value: String(last?.to_status ?? "UNKNOWN") },
        sourcePath: `inspect.resolutions[${lastIdx}].to_status`,
        facts: chain.map((step) => {
          const stepIdx = inspect.resolutions.findIndex(
            (r) => r.resolution_seq === step.resolution_seq,
          );
          return {
            label: `step ${step.resolution_seq} (${step.actor})`,
            value: `${String(step.from_status)} → ${String(step.to_status)}`,
            path: `inspect.resolutions[${stepIdx}].to_status`,
          };
        }),
        rank: RANK.resolution,
        lateral: false,
        orderKey: `${last?.created_at ?? ""}:${String(finding.finding_id).padStart(6, "0")}`,
      });
      edges.push({
        id: `edge:resolved-through:${finding.finding_id}`,
        from: id,
        to: resolutionId,
        relation: "resolved-through",
        stroke: "solid",
        evidencePath: `inspect.resolutions[${lastIdx}].finding_id`,
      });
    }
  });

  // Deterministic global order: (rank, lateral, orderKey, id).
  nodes.sort(
    (a, b) =>
      a.rank - b.rank ||
      Number(a.lateral) - Number(b.lateral) ||
      a.orderKey.localeCompare(b.orderKey) ||
      a.id.localeCompare(b.id),
  );
  edges.sort((a, b) => a.id.localeCompare(b.id));
  annotations.sort((a, b) => a.beforeRank - b.beforeRank);

  return {
    effectId,
    nodes,
    edges,
    annotations,
    integrityFailure: !inspect.integrity.matches,
    notes,
  };
}
