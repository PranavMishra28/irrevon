import type { CapabilityDeclaration } from "@/shared/contracts/generated/capability-declaration";
import type { EffectRecord } from "@/shared/contracts/generated/effect-record";
import type { ReconciliationFinding } from "@/shared/contracts/generated/reconciliation-finding";
import type {
  Classification,
  Lifecycle,
  ProbeResult,
  ResolutionStatus,
  TransitionActor,
} from "@/shared/contracts/generated/state-model";

/**
 * Read-surface payload types. Envelope framing is ratified in RFC-002 §9
 * ({schema_version, data[], has_more, next_cursor, as_of}); the inspect
 * payload mirrors `detent inspect --json` exactly (src/detent/cli/inspect_cmd.py
 * at the pinned engine commit — see fixtures/canonical/provenance.json).
 * Record/finding items are the schema-generated exchange shapes.
 */

export const SUPPORTED_SCHEMA_VERSION = "1";

export interface QueryEnvelope<T> {
  schema_version: string;
  data: T[];
  has_more: boolean;
  next_cursor: string | null;
  as_of: string;
}

/** Q1 item per RFC-002 §9: record view + findings + current classification. */
export interface EffectListItem {
  record: EffectRecord;
  classification: Classification | "UNRECONCILED";
  finding: ReconciliationFinding | null;
}

export type EffectsEnvelope = QueryEnvelope<EffectListItem>;
export type FindingsEnvelope = QueryEnvelope<ReconciliationFinding>;

export interface AdaptersPayload {
  schema_version: string;
  data: CapabilityDeclaration[];
  as_of: string;
}

// ── `detent inspect --json` (verbatim CLI shape) ─────────────────────────────

export interface InspectTransition {
  transition_seq: number;
  step: number;
  operation_id: string;
  from_state: Lifecycle | null;
  to_state: Lifecycle;
  cause: string;
  actor: TransitionActor;
  evidence: Record<string, unknown>;
  created_at: string;
}

export interface InspectReceipt {
  receipt_id: number;
  operation_id: string;
  attempt_no: number;
  kind: string;
  idempotency_key: string;
  transport_outcome: string;
  failure_kind: string | null;
  destination_ref: string | null;
  recorded_by: string;
  recorded_at: string;
}

export interface InspectFinding {
  finding_id: number;
  effect_id: string | null;
  adapter_id: string;
  destination_ref: string | null;
  classification: Classification | (string & {});
  excess_effect_count: number | null;
  evidence: Record<string, unknown>;
  evidence_digest: string;
  created_by: string;
  created_at: string;
}

export interface InspectResolution {
  resolution_seq: number;
  finding_id: number;
  from_status: ResolutionStatus | (string & {});
  to_status: ResolutionStatus | (string & {});
  evidence: Record<string, unknown>;
  actor: string;
  created_at: string;
}

export interface GateCheck {
  check: string;
  status: "passed" | "denied" | (string & {});
  evidence?: DenyEvidence;
}

export interface BlockingExecution {
  step: number;
  frontier: Lifecycle | (string & {});
  finding_ids: number[];
  receipt_ids: number[];
  execution_id: number;
  operation_id: string;
}

export interface DenyEvidence {
  cause?: string;
  input_digest?: string;
  parameter_variants?: string[];
  blocking_executions?: BlockingExecution[];
  [k: string]: unknown;
}

export interface GateDecision {
  decision_id: number;
  variant: string;
  outcome: "ALLOW" | "DENY" | (string & {});
  deny_check: string | null;
  checks: GateCheck[];
  evidence: DenyEvidence;
  created_at: string;
}

export interface InspectProbe {
  probe_id: number;
  probe_kind: string;
  result: ProbeResult | (string & {});
  n_found: number | null;
  queried_at: string;
}

export interface InspectPayload {
  schema_version: string;
  kind: "effect";
  record: {
    effect_id: string;
    effect_type: string;
    effect_class: string;
    scope: string;
    stable_ids: Record<string, string>;
    adapter_id: string;
    lifecycle: Lifecycle | (string & {});
  };
  timeline: InspectTransition[];
  receipts: InspectReceipt[];
  findings: InspectFinding[];
  resolutions: InspectResolution[];
  gate_decisions: GateDecision[];
  probes: InspectProbe[];
  classification: Classification | "UNRECONCILED" | (string & {});
  integrity: { recomputed_intent_id: string; matches: boolean };
}

// ── doctor / demo artifact (verbatim CLI shapes) ─────────────────────────────

export interface DoctorCheck {
  name: string;
  status: "ok" | "warn" | "fail" | (string & {});
  message: string;
  hint: string | null;
}

export interface DoctorPayload {
  schema_version: string;
  checks: DoctorCheck[];
  [k: string]: unknown;
}

export interface DemoEvent {
  event: string;
  [k: string]: unknown;
}

export interface DemoSummary {
  schema_version: string;
  seed: number;
  detent_leg: {
    destination_effects?: number;
    duplicate_rejected?: boolean;
    reconciled?: string;
    effect_id?: string;
  };
  b5_leg: { destination_effects?: number; duplicate_created?: boolean };
  contrast_holds: boolean;
}

export interface DemoArtifact {
  schema_version: string;
  events: DemoEvent[];
  summary: DemoSummary;
}
