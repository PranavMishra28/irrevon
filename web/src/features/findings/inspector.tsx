import type { ReconciliationFinding } from "@/shared/contracts/generated/reconciliation-finding";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { truncateEffectId } from "@/shared/lib/ids";
import { X } from "@/shared/ui/icons";
import { IconButton } from "@/shared/ui/primitives/button";
import { PanelHeader, SunkenWell } from "@/shared/ui/primitives/panel";

/**
 * Selected-finding inspector (REDESIGN-BRIEF §5.5). Effect-backed findings
 * link into the owning investigation; a destination-keyed orphan shows the
 * paired subject/absence view — the recorded destination observation beside
 * an explicit absent-ledger slot. The absence is rendered text, never empty
 * space, and no causal edge is fabricated between the pair. Digest-only
 * evidence is stated as unverifiable here — never "verified".
 */
export function FindingInspector({
  finding,
  onClose,
}: {
  finding: ReconciliationFinding;
  onClose: () => void;
}) {
  const isOrphan = !("effect_id" in finding.subject);
  const rawStatus = finding.resolution.status;
  const resolutionStatus = typeof rawStatus === "string" ? rawStatus : "UNKNOWN";
  const resolvedAt =
    typeof finding.resolution.resolved_at === "string" ? finding.resolution.resolved_at : null;

  return (
    <section
      aria-label={`Finding ${finding.finding_id}`}
      data-testid="finding-inspector"
      className={
        "flex min-w-0 flex-col rounded-(--radius-structural) border border-border-subtle " +
        "bg-layer-panel shadow-(--sys-edge-light)"
      }
    >
      <PanelHeader
        title="Finding"
        meta={finding.finding_id}
        actions={
          <IconButton label="Close inspector" onClick={onClose}>
            <X size={14} />
          </IconButton>
        }
      />
      <div className="flex min-w-0 flex-col gap-4 p-(--dt-panel-pad)">
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5">
          <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
            Classification
          </dt>
          <dd>
            {finding.classification === "DUPLICATE" &&
            finding.excess_effect_count !== undefined ? (
              <FindingBadge value="DUPLICATE" excessEffectCount={finding.excess_effect_count} />
            ) : (
              <FindingBadge value={finding.classification} />
            )}
          </dd>
          <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
            Resolution
          </dt>
          <dd className="flex flex-wrap items-baseline gap-2">
            <ResolutionTag value={resolutionStatus} />
            {resolvedAt !== null ? (
              <time
                dateTime={resolvedAt}
                className="machine-id font-mono text-2xs text-text-tertiary"
              >
                resolved {resolvedAt.slice(0, 19).replace("T", " ")}Z
              </time>
            ) : null}
          </dd>
          <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
            Created
          </dt>
          <dd className="machine-id font-mono text-xs text-text-primary">
            <time dateTime={finding.created_at}>
              {finding.created_at.slice(0, 19).replace("T", " ")}Z
            </time>
            <span className="text-text-tertiary"> · by {finding.created_by}</span>
          </dd>
          <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
            Adapter
          </dt>
          <dd className="machine-id font-mono text-xs text-text-primary">
            {finding.adapter_id}
          </dd>
        </dl>

        {isOrphan ? (
          <OrphanPairedView finding={finding} />
        ) : (
          <div>
            <h3 className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
              Subject — ledger effect
            </h3>
            {"effect_id" in finding.subject ? (
              <p className="mt-1.5">
                <a
                  href={`/effects/${finding.subject.effect_id}`}
                  className="machine-id font-mono text-xs text-accent underline underline-offset-2"
                >
                  {truncateEffectId(finding.subject.effect_id)}
                </a>
                <span className="ml-2 text-2xs text-text-tertiary">
                  opens the causal investigation
                </span>
              </p>
            ) : null}
          </div>
        )}

        <div>
          <h3 className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
            Evidence
          </h3>
          <SunkenWell className="mt-1.5">
            <p className="machine-id font-mono text-2xs break-all text-text-primary">
              {finding.evidence_digest}
            </p>
            <p className="mt-1.5 text-2xs text-text-secondary">
              redaction: <span className="font-mono">{finding.evidence.redaction}</span> — the
              evidence bundle is served digest-only. A digest addresses the evidence; it does
              not verify it here.
            </p>
          </SunkenWell>
        </div>
      </div>
    </section>
  );
}

/**
 * The orphan pair: a recorded destination observation beside an explicit,
 * labeled absent-ledger slot. The two are adjacent but unconnected — the
 * served contract carries no match-order evidence to draw an edge with.
 */
export function OrphanPairedView({ finding }: { finding: ReconciliationFinding }) {
  if ("effect_id" in finding.subject) return null;
  return (
    <div>
      <h3 className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
        Subject — destination-keyed (no ledger record)
      </h3>
      <div className="mt-1.5 grid grid-cols-1 gap-2 min-[480px]:grid-cols-2">
        <div className="dt-hatched rounded-(--radius-structural) border border-border p-3">
          <p className="font-mono text-2xs font-medium tracking-wide text-text-secondary uppercase">
            Destination observation
          </p>
          <dl className="mt-1.5 flex flex-col gap-1">
            <div>
              <dt className="font-mono text-2xs text-text-tertiary">adapter_id</dt>
              <dd className="machine-id font-mono text-xs text-text-primary">
                {finding.subject.adapter_id}
              </dd>
            </div>
            <div>
              <dt className="font-mono text-2xs text-text-tertiary">destination_ref</dt>
              <dd className="machine-id font-mono text-xs break-all text-text-primary">
                {finding.subject.destination_ref}
              </dd>
            </div>
          </dl>
          <p className="mt-1.5 text-2xs text-text-tertiary">
            observed at the destination by the sweep — not ledger truth
          </p>
        </div>
        <div className="rounded-(--radius-structural) border border-dashed border-border p-3">
          <p className="font-mono text-2xs font-medium tracking-wide text-text-secondary uppercase">
            Absent ledger record
          </p>
          <p className="mt-1.5 text-sm text-text-primary">
            No ledger record — this destination effect was never intended through Detent.
          </p>
          <p className="mt-1.5 text-2xs text-text-tertiary">
            The pair is shown adjacent, not connected: the served evidence is digest-only, so no
            failed-match edge can be drawn.
          </p>
        </div>
      </div>
    </div>
  );
}
