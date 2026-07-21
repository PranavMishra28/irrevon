import type { CapabilityDeclaration } from "@/shared/contracts/generated/capability-declaration";
import { EvidenceQualityTag, TierMeter } from "@/shared/domain/status/supporting-status";

const dt = "font-mono text-2xs text-text-tertiary uppercase tracking-wide";
const dd = "text-sm text-text-primary";

/** Field-for-field view of a real, schema-validated capability declaration. */
export function DeclarationCard({ declaration }: { declaration: CapabilityDeclaration }) {
  return (
    <section className="rounded-(--radius-structural) border border-border bg-surface-1 p-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="font-mono text-base font-semibold text-text-primary">
          {declaration.adapter}
        </h2>
        <TierMeter value={declaration.tier} />
        <EvidenceQualityTag value={declaration.evidence_quality} />
        <span className="font-mono text-2xs text-text-tertiary">
          api {declaration.api_version}
        </span>
      </div>
      <p className="mt-1 text-sm text-text-secondary">{declaration.destination}</p>
      <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2">
        <dt className={dt}>idempotency</dt>
        <dd className={dd}>
          {declaration.idempotency.supported
            ? `supported (window ${declaration.idempotency.window ?? "unstated"})`
            : "not supported — recorded as a passing expected negative contract test"}
        </dd>
        <dt className={dt}>queryable</dt>
        <dd className={dd}>
          {declaration.queryable.supported
            ? `by ${declaration.queryable.by?.join(", ") ?? "(unstated keys)"}`
            : "not queryable"}
        </dd>
        <dt className={dt}>client_ref_field</dt>
        <dd className={`${dd} font-mono text-xs`}>
          {declaration.client_ref_field ?? "none — the strongest reconcile hook is absent"}
        </dd>
        <dt className={dt}>list_queryable</dt>
        <dd className={dd}>
          {declaration.list_queryable
            ? "yes — orphan sweep is feasible"
            : "no — orphan sweep is not feasible"}
        </dd>
        <dt className={dt}>consistency</dt>
        <dd className={`${dd} font-mono text-xs`}>
          status lag {declaration.consistency.status_settlement_lag ?? "unbounded/unknown"} ·
          listing lag {declaration.consistency.listing_lag ?? "unbounded/unknown"}
        </dd>
        <dt className={dt}>compensation_hook</dt>
        <dd className={`${dd} font-mono text-xs`}>
          {declaration.compensation_hook ?? "none declared"}
        </dd>
        <dt className={dt}>citations</dt>
        <dd className="flex flex-col gap-0.5">
          {declaration.citations.map((citation) => (
            <span key={citation} className="font-mono text-xs break-all text-text-secondary">
              {citation}
            </span>
          ))}
        </dd>
      </dl>
      <p className="mt-4 border-t border-border-subtle pt-3 text-xs text-text-secondary">
        Boundary: this declaration is what the destination is contracted to do — nothing here
        claims live contract-test results or drift status; those land with the M4 adapter
        workstream.
      </p>
    </section>
  );
}
