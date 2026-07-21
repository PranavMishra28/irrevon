import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/shared/api/client";
import { queryKeys } from "@/shared/api/query-keys";
import type { AdaptersPayload, InspectPayload } from "@/shared/api/types";
import type { EffectRecord } from "@/shared/contracts/generated/effect-record";
import {
  CLASSIFICATION_ATTACHMENT,
  RESOLUTION_LEGALITY,
  TERMINAL_LIFECYCLE_STATES,
  type Classification,
  type Lifecycle,
} from "@/shared/contracts/generated/state-model";
import { EvidenceQualityTag, TierMeter } from "@/shared/domain/status/supporting-status";

/**
 * Context rail: factual fields only — authority presence, adapter binding,
 * and the generated legal-state explanation. No recommendation, score, rank,
 * or action button exists here by design.
 */

const dt = "font-mono text-2xs text-text-tertiary uppercase tracking-wide";
const dd = "font-mono text-xs text-text-primary break-all";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-(--radius-structural) border border-border bg-surface-1 p-4">
      <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

export function ContextRail({
  payload,
  record,
}: {
  payload: InspectPayload;
  record: EffectRecord | undefined;
}) {
  const adapters = useQuery({
    queryKey: queryKeys.adapters(),
    queryFn: () => apiGet<AdaptersPayload>("/api/v1/adapters"),
  });
  const declaration = adapters.data?.data.find((d) => d.adapter === payload.record.adapter_id);

  const lifecycle = payload.record.lifecycle as Lifecycle;
  const isTerminal = (TERMINAL_LIFECYCLE_STATES as readonly string[]).includes(lifecycle);
  const attachment = (CLASSIFICATION_ATTACHMENT as Record<string, Record<string, string>>)[
    lifecycle
  ];
  const legalClassifications = attachment
    ? Object.entries(attachment)
        .filter(([, legality]) => legality === "LEGAL")
        .map(([classification]) => classification)
    : [];
  const openFinding = payload.findings.find((finding) => {
    const chain = payload.resolutions.filter((r) => r.finding_id === finding.finding_id);
    const status = chain.length > 0 ? chain[chain.length - 1]?.to_status : "OPEN";
    return status !== "CLOSED";
  });
  const legalActions = openFinding
    ? Object.entries(
        (RESOLUTION_LEGALITY as Record<string, Record<string, string>>)[
          openFinding.classification as Classification
        ] ?? {},
      )
        .filter(([, legality]) => legality !== "ILLEGAL")
        .map(([action, legality]) => `${action}${legality === "AUTO" ? " (auto)" : ""}`)
    : [];

  return (
    <div className="flex flex-col gap-4">
      <Card title="Authority">
        <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
          <dt className={dt}>authority_ref</dt>
          <dd className={dd}>
            {record?.authority_ref ?? (
              <span className="text-text-tertiary">record view unavailable</span>
            )}
          </dd>
          <dt className={dt}>stamped_at</dt>
          <dd className={dd}>{record?.stamped_at ?? "—"}</dd>
        </dl>
        <p className="mt-2 text-2xs text-text-tertiary">
          Freshness is checked deterministically at the commit gate; these are the stamped
          facts, not a judgement.
        </p>
      </Card>

      <Card title="Adapter">
        <dl className="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
          <dt className={dt}>adapter_id</dt>
          <dd className={dd}>{payload.record.adapter_id}</dd>
          {declaration ? (
            <>
              <dt className={dt}>destination</dt>
              <dd className="text-xs text-text-primary">{declaration.destination}</dd>
              <dt className={dt}>tier</dt>
              <dd className="flex items-center gap-2">
                <TierMeter value={declaration.tier} />
                <EvidenceQualityTag value={declaration.evidence_quality} />
              </dd>
              <dt className={dt}>api_version</dt>
              <dd className={dd}>{declaration.api_version}</dd>
            </>
          ) : null}
          {record ? (
            <>
              <dt className={dt}>declaration</dt>
              <dd className={dd} title={record.declaration_digest}>
                {record.declaration_digest.slice(0, 23)}…
              </dd>
            </>
          ) : null}
        </dl>
        {declaration ? (
          <p className="mt-2 text-2xs text-text-secondary">
            {declaration.tier === "C2"
              ? "Queryable, no dependable native idempotency: duplicates are detected by authoritative query; redispatch is safe only after confirmed absence."
              : declaration.tier === "C1"
                ? "Idempotency-keyed: duplicates prevented natively within the replay window."
                : "Opaque: lost effects are undetectable — an impossibility boundary."}
          </p>
        ) : null}
      </Card>

      <Card title="Legal state (generated)">
        <p className="text-xs text-text-secondary">
          Lifecycle <span className="font-mono">{payload.record.lifecycle}</span>
          {isTerminal ? " is terminal for this execution" : " is not terminal"}.{" "}
          {legalClassifications.length > 0
            ? `Classifications legally attachable here: ${legalClassifications.join(", ")}.`
            : "No classification may legally attach at this frontier."}
        </p>
        {openFinding ? (
          <p className="mt-2 text-xs text-text-secondary">
            Open finding <span className="font-mono">{openFinding.classification}</span> —
            actions the ratified table permits: {legalActions.join(", ")}. Resolution happens
            outside this read-only workbench.
          </p>
        ) : null}
        <p className="mt-2 text-2xs text-text-tertiary">
          Derived from the generated RFC-002 §3 tables; descriptive, never advice.
        </p>
      </Card>
    </div>
  );
}
