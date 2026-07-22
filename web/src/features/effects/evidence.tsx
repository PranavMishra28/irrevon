import { useState } from "react";
import type { EffectRecord } from "@/shared/contracts/generated/effect-record";
import type { InspectPayload } from "@/shared/api/types";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { TransportOutcomeInline } from "@/shared/domain/status/supporting-status";
import { truncateOperationId } from "@/shared/lib/ids";
import { GateCheckChip, GateOutcomeText, IntegrityLine } from "@/shared/domain/status/verdicts";
import { useAnnouncer } from "@/shared/ui/layout/live-regions";
import { Copy, Eye, EyeOff } from "@/shared/ui/icons";
import { IconButton } from "@/shared/ui/primitives/button";

/**
 * Evidence region, digest-first progressive disclosure: summary → structured
 * <dl> → exact JSON. Digest-only evidence is a commitment with bytes
 * unavailable — it is never described as missing and never marked verified.
 */

function Digest({ value }: { value: string }) {
  const { announce } = useAnnouncer();
  return (
    <span className="inline-flex max-w-full items-center gap-1">
      <span className="truncate font-mono text-2xs text-text-secondary" title={value}>
        {value.slice(0, 23)}…
      </span>
      <IconButton
        label={`Copy digest ${value.slice(0, 14)}`}
        onClick={() => {
          void navigator.clipboard.writeText(value).then(() => {
            announce("Digest copied");
          });
        }}
      >
        <Copy size={12} />
      </IconButton>
    </span>
  );
}

function SectionCard({
  title,
  lead,
  children,
}: {
  title: string;
  lead?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-(--radius-structural) border border-border-subtle bg-layer-panel p-4 shadow-(--sys-edge-light)">
      <h3 className="text-base font-semibold text-text-primary">{title}</h3>
      {lead !== undefined ? <p className="mt-1 text-xs text-text-secondary">{lead}</p> : null}
      <div className="mt-3">{children}</div>
    </section>
  );
}

const dt = "font-mono text-2xs text-text-tertiary uppercase tracking-wide";
const dd = "font-mono text-xs text-text-primary break-all";

export function IdentitySection({
  payload,
  record,
}: {
  payload: InspectPayload;
  record: EffectRecord | undefined;
}) {
  const [revealed, setRevealed] = useState(false);
  const entries = Object.entries(payload.record.stable_ids);
  const redacted = entries.every(([, v]) => v.startsWith("<redacted"));

  return (
    <SectionCard
      title="Identity"
      lead="intent_id = SHA-256 over the RFC 8785-canonical {stable_ids, effect_type, scope}. Stable-id values are redacted by default; keys are the evidence."
    >
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5">
        <dt className={dt}>stable_ids</dt>
        <dd className="flex flex-col gap-0.5">
          {entries.map(([key, value]) => (
            <span key={key} className={dd}>
              {key}
              {": "}
              <span className="text-text-tertiary">
                {redacted && !revealed ? "‹redacted›" : value}
              </span>
            </span>
          ))}
        </dd>
        <dt className={dt}>effect_type</dt>
        <dd className={dd}>{payload.record.effect_type}</dd>
        <dt className={dt}>scope</dt>
        <dd className={dd}>{payload.record.scope}</dd>
        {record ? (
          <>
            <dt className={dt}>parameters_digest</dt>
            <dd>
              <Digest value={record.parameters_digest} />
            </dd>
            <dt className={dt}>declaration_digest</dt>
            <dd>
              <Digest value={record.declaration_digest} />
            </dd>
          </>
        ) : null}
        <dt className={dt}>integrity</dt>
        <dd className="text-xs">
          <IntegrityLine matches={payload.integrity.matches} />
        </dd>
      </dl>
      {redacted ? (
        <p className="mt-2 text-2xs text-text-tertiary">
          Values were redacted at capture time by the CLI default; nothing to reveal in this
          fixture.
          {revealed ? "" : " "}
          <button
            type="button"
            className="inline-flex items-center gap-1 text-accent hover:underline"
            onClick={() => {
              setRevealed((r) => !r);
            }}
          >
            {revealed ? <EyeOff size={12} /> : <Eye size={12} />}
            {revealed ? "show placeholders" : "show raw field"}
          </button>
        </p>
      ) : null}
    </SectionCard>
  );
}

export function AttemptsSection({ payload }: { payload: InspectPayload }) {
  if (payload.receipts.length === 0) {
    return (
      <SectionCard title="Dispatch attempts">
        <p className="text-sm text-text-secondary">
          No dispatch attempt exists — nothing has crossed the boundary.
        </p>
      </SectionCard>
    );
  }
  return (
    <SectionCard
      title="Dispatch attempts"
      lead="Every attempt across every execution; the idempotency key derives only from the operation id."
    >
      <ul className="flex flex-col divide-y divide-border-subtle">
        {payload.receipts.map((receipt) => (
          <li key={receipt.receipt_id} id={`receipt-${receipt.receipt_id}`} className="py-2">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="font-mono text-xs text-text-primary">
                rcpt_{String(receipt.receipt_id).padStart(20, "0")}
              </span>
              <TransportOutcomeInline value={receipt.transport_outcome} />
              {receipt.failure_kind !== null ? (
                <span className="font-mono text-2xs text-text-secondary">
                  failure_kind={receipt.failure_kind}
                </span>
              ) : null}
            </div>
            <dl className="mt-1.5 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
              <dt className={dt}>operation</dt>
              <dd className={dd} title={receipt.operation_id}>
                {truncateOperationId(receipt.operation_id)} · attempt {receipt.attempt_no} (
                {receipt.kind})
              </dd>
              <dt className={dt}>idempotency_key</dt>
              <dd className={dd} title={receipt.idempotency_key}>
                {truncateOperationId(receipt.idempotency_key)}
              </dd>
              <dt className={dt}>sent</dt>
              <dd className={dd}>
                <time dateTime={receipt.recorded_at}>{receipt.recorded_at}</time> · recorded by{" "}
                {receipt.recorded_by}
              </dd>
              <dt className={dt}>destination_ref</dt>
              <dd className={dd}>
                {receipt.destination_ref ?? (
                  <span className="text-text-tertiary">absent — no response carried one</span>
                )}
              </dd>
            </dl>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}

export function ReconciliationSection({ payload }: { payload: InspectPayload }) {
  const stillAmbiguous = payload.record.lifecycle === "AMBIGUOUS";
  return (
    <SectionCard
      title="Reconciliation"
      lead="Query basis, verdicts, and resolution history. Evidence bundles are digest-only commitments until the redaction pipeline exists — committed, not missing, never marked verified."
    >
      {payload.probes.length > 0 ? (
        <div>
          <h4 className={dt}>status probes (query basis)</h4>
          <ul className="mt-1 flex flex-col gap-1">
            {payload.probes.map((probe) => (
              <li key={probe.probe_id} className="font-mono text-xs text-text-primary">
                probe {probe.probe_id} ({probe.probe_kind}): {probe.result}
                {probe.n_found !== null ? ` · n=${probe.n_found}` : ""}
                <span className="text-text-tertiary"> · {probe.queried_at}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-text-secondary">No status probe has run for this effect.</p>
      )}
      {stillAmbiguous ? (
        <p className="mt-3 border-l-2 border-border-strong pl-2 text-xs text-text-secondary">
          Still ambiguous: the destination has not been queried to adjudication yet. This is an
          open question with a procedure, not an alarm.
        </p>
      ) : null}
      {payload.findings.length > 0 ? (
        <ul className="mt-3 flex flex-col gap-3 border-t border-border-subtle pt-3">
          {payload.findings.map((finding) => {
            const chain = payload.resolutions.filter(
              (r) => r.finding_id === finding.finding_id,
            );
            return (
              <li key={finding.finding_id} id={`finding-${finding.finding_id}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-text-primary">
                    fnd_{String(finding.finding_id).padStart(20, "0")}
                  </span>
                  {finding.classification === "DUPLICATE" &&
                  finding.excess_effect_count !== null ? (
                    <FindingBadge
                      value="DUPLICATE"
                      excessEffectCount={finding.excess_effect_count}
                    />
                  ) : (
                    <FindingBadge value={finding.classification} />
                  )}
                  <span className="text-2xs text-text-tertiary">
                    by {finding.created_by} · {finding.created_at}
                  </span>
                </div>
                <dl className="mt-1 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
                  <dt className={dt}>evidence</dt>
                  <dd className="flex items-center gap-2">
                    <Digest value={finding.evidence_digest} />
                    <span className="text-2xs text-text-tertiary">
                      digest-only (bundle bytes unavailable by policy)
                    </span>
                  </dd>
                  <dt className={dt}>resolution</dt>
                  <dd className="flex flex-wrap items-center gap-1.5">
                    {chain.length === 0 ? (
                      <ResolutionTag value="OPEN" />
                    ) : (
                      chain.map((r) => (
                        <span key={r.resolution_seq} className="flex items-center gap-1.5">
                          <ResolutionTag value={r.from_status} />
                          <span aria-hidden className="text-text-tertiary">
                            →
                          </span>
                          <span className="sr-only">to</span>
                          <ResolutionTag value={r.to_status} />
                          <span className="text-2xs text-text-tertiary">({r.actor})</span>
                        </span>
                      ))
                    )}
                  </dd>
                </dl>
              </li>
            );
          })}
        </ul>
      ) : null}
    </SectionCard>
  );
}

export function DecisionLogSection({ payload }: { payload: InspectPayload }) {
  if (payload.gate_decisions.length === 0) {
    return (
      <SectionCard title="Decision log">
        <p className="text-sm text-text-secondary">No gate decision has been recorded.</p>
      </SectionCard>
    );
  }
  return (
    <SectionCard
      title="Decision log"
      lead="Every gate evaluation — allow and deny — with the ordered check list and exact evidence."
    >
      <ul className="flex flex-col gap-3">
        {payload.gate_decisions.map((decision) => (
          <li key={decision.decision_id} id={`decision-${decision.decision_id}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xs text-text-primary">
                decision {decision.decision_id} [{decision.variant}]
              </span>
              <GateOutcomeText value={decision.outcome} />
              <span className="text-2xs text-text-tertiary">{decision.created_at}</span>
            </div>
            <ol className="mt-1 flex flex-wrap gap-1" aria-label="Ordered gate checks">
              {decision.checks.map((check) => (
                <li key={check.check}>
                  <GateCheckChip check={check.check} status={check.status} />
                </li>
              ))}
            </ol>
            {decision.deny_check !== null && decision.evidence.cause !== undefined ? (
              <p className="mt-1.5 text-xs text-text-primary">
                Denied by <span className="font-mono">{decision.deny_check}</span>: cause{" "}
                <span className="font-mono">{decision.evidence.cause}</span>
                {decision.evidence.blocking_executions?.map((blocking) => (
                  <span key={blocking.execution_id}>
                    {" — cites execution "}
                    <span className="font-mono">
                      {truncateOperationId(blocking.operation_id)}
                    </span>{" "}
                    at <span className="font-mono">{blocking.frontier}</span> with{" "}
                    {blocking.receipt_ids.length} receipt(s) and {blocking.finding_ids.length}{" "}
                    finding(s)
                  </span>
                ))}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}

export function ResynthesisSection({
  payload,
  record,
}: {
  payload: InspectPayload;
  record: EffectRecord | undefined;
}) {
  const deny = payload.gate_decisions.find(
    (d) => d.deny_check === "dedup" && (d.evidence.parameter_variants?.length ?? 0) > 0,
  );
  if (!deny) return null;
  const variants = deny.evidence.parameter_variants ?? [];

  return (
    <SectionCard
      title="Re-synthesis exhibit"
      lead="Same stable business identity, different model-generated arguments. Digest inequality is the whole claim — payload text is never reconstructed."
    >
      {/* Identity-convergence band */}
      <div className="rounded-t-(--radius-structural) border border-border-strong bg-layer-sunken p-3">
        <p className={dt}>identity — convergent</p>
        <p className="mt-1 font-mono text-xs break-all text-text-primary">
          {payload.record.effect_id}
        </p>
        <p className="mt-1 text-2xs text-text-secondary">
          Both requests hash to this one effect_id: same stable_ids keys (
          {Object.keys(payload.record.stable_ids).join(", ")}), same effect_type (
          {payload.record.effect_type}), same scope ({payload.record.scope}).
        </p>
      </div>
      {/* Difference band */}
      <div className="rounded-b-(--radius-structural) border border-t-0 border-border p-3">
        <p className={dt}>parameters — divergent (non-identity)</p>
        <dl className="mt-1 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
          <dt className="font-mono text-2xs text-text-tertiary">original</dt>
          <dd>
            {record ? (
              <Digest value={record.parameters_digest} />
            ) : (
              <span className="text-2xs text-text-tertiary">record view unavailable</span>
            )}
          </dd>
          {variants.map((variant) => (
            <div key={variant} className="col-span-2 grid grid-cols-subgrid">
              <dt className="font-mono text-2xs text-text-tertiary">variant</dt>
              <dd>
                <Digest value={variant} />
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-2 text-2xs text-text-secondary">
          The recorded variant digest differs from the original parameters digest; the gate
          answered the retry with the denial above instead of a second effect.
        </p>
      </div>
    </SectionCard>
  );
}

/** Minimal JSON highlighter — no editor dependency. */
function highlightJson(json: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re =
    /("(?:[^"\\]|\\.)*")(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = re.exec(json)) !== null) {
    if (match.index > last) parts.push(json.slice(last, match.index));
    const [full, str, colon, keyword] = match;
    if (str !== undefined) {
      parts.push(
        <span key={i++} className={colon ? "text-text-secondary" : "text-text-primary"}>
          {str}
        </span>,
      );
      if (colon) parts.push(colon);
    } else if (keyword !== undefined) {
      parts.push(
        <span key={i++} className="text-text-tertiary italic">
          {keyword}
        </span>,
      );
    } else {
      parts.push(
        <span key={i++} className="tabular text-text-secondary">
          {full}
        </span>,
      );
    }
    last = match.index + full.length;
  }
  parts.push(json.slice(last));
  return parts;
}

export function RawJsonSection({ payload }: { payload: InspectPayload }) {
  return (
    <SectionCard
      title="Raw response"
      lead="The exact irrevon inspect --json payload this page is rendered from."
    >
      <details>
        <summary className="cursor-default text-xs text-accent hover:underline">
          Show exact JSON ({(JSON.stringify(payload).length / 1024).toFixed(1)} KB)
        </summary>
        <pre className="mt-2 max-h-96 overflow-auto rounded-(--radius-control) border border-border-subtle bg-layer-sunken p-3 font-mono text-2xs leading-relaxed">
          {highlightJson(JSON.stringify(payload, null, 2))}
        </pre>
      </details>
    </SectionCard>
  );
}
