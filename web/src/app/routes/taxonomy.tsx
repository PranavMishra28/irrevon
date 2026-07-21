import { createFileRoute, notFound } from "@tanstack/react-router";
import { isMockMode } from "@/app/data-mode";
import {
  CLASSIFICATIONS,
  EFFECT_CLASSES,
  LIFECYCLE_STATES,
  RESOLUTION_STATUSES,
  TRANSPORT_OUTCOMES,
} from "@/shared/contracts/generated/state-model";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { LifecyclePill } from "@/shared/domain/status/lifecycle-pill";
import { ResolutionNotApplicable, ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { StatusTriplet } from "@/shared/domain/status/status-triplet";
import {
  EffectClassBadge,
  EvidenceQualityTag,
  TierMeter,
  TransportOutcomeInline,
} from "@/shared/domain/status/supporting-status";
import { UnknownStatus } from "@/shared/domain/status/unknown-status";
import { Page } from "@/shared/ui/layout/page";
import { SeatMark } from "@/shared/ui/layout/mark";
import { Button, IconButton } from "@/shared/ui/primitives/button";
import { Copy } from "@/shared/ui/icons";

/**
 * Dev-only gallery. Excluded from the production route tree: a live
 * production build 404s this path. Status-component swatches join in the
 * schema-dependent slices.
 */
export const Route = createFileRoute("/taxonomy")({
  beforeLoad: () => {
    if (import.meta.env.PROD && !isMockMode) throw notFound();
  },
  component: TaxonomyPage,
});

const SURFACES = ["canvas", "surface-1", "surface-2", "surface-3"] as const;
const TEXT_ROLES = ["primary", "secondary", "tertiary", "disabled"] as const;
const TYPE_SCALE = [
  ["text-2xs", "11px — uppercase micro-labels only"],
  ["text-xs", "12px — dense cells, pills, captions"],
  ["text-sm", "13px — default body, comfortable cells"],
  ["text-base", "14px — forms, dialogs, prose"],
  ["text-lg", "16px — panel titles"],
  ["text-xl", "20px — page titles"],
  ["text-2xl", "24px — KPI numerals (unused in v0.1)"],
] as const;

function StatusMatrix({ grayscale = false }: { grayscale?: boolean }) {
  return (
    <div
      className="flex flex-col gap-3 rounded-(--radius-structural) border border-border bg-surface-1 p-5"
      style={grayscale ? { filter: "grayscale(1)" } : undefined}
    >
      <div className="flex flex-wrap items-center gap-2">
        {LIFECYCLE_STATES.map((v) => (
          <LifecyclePill key={v} value={v} />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <FindingBadge value="UNRECONCILED" />
        {CLASSIFICATIONS.map((v) =>
          v === "DUPLICATE" ? (
            <FindingBadge key={v} value={v} excessEffectCount={2} />
          ) : (
            <FindingBadge key={v} value={v} />
          ),
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {RESOLUTION_STATUSES.map((v) => (
          <ResolutionTag key={v} value={v} />
        ))}
        <ResolutionNotApplicable />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {EFFECT_CLASSES.map((v) => (
          <EffectClassBadge key={v} value={v} />
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {TRANSPORT_OUTCOMES.map((v) => (
          <TransportOutcomeInline key={v} value={v} />
        ))}
        <TierMeter value="C1" />
        <TierMeter value="C2" />
        <TierMeter value="C3" />
        <EvidenceQualityTag value="VF" />
        <EvidenceQualityTag value="EI" />
        <UnknownStatus dimension="lifecycle" value="NOT_A_STATE" />
      </div>
    </div>
  );
}

function TaxonomyPage() {
  return (
    <Page
      title="Taxonomy gallery"
      lead="Dev-only: the full status taxonomy over the generated enums, plus tokens, type, and primitives, in the active theme and density."
    >
      <div className="flex max-w-4xl flex-col gap-6">
        <section>
          <h2 className="text-lg font-semibold text-text-primary">
            Status taxonomy — three channels, never conflated
          </h2>
          <div className="mt-3">
            <StatusMatrix />
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-text-primary">Composition (A · B · C)</h2>
          <div className="mt-3 flex flex-col gap-3 rounded-(--radius-structural) border border-border bg-surface-1 p-5">
            <StatusTriplet lifecycle="AMBIGUOUS" classification="UNRECONCILED" />
            <StatusTriplet
              lifecycle="SETTLED_COMMITTED"
              classification="CONFIRMED_UNIQUE"
              resolution="CLOSED"
            />
            <StatusTriplet
              lifecycle="SETTLED_COMMITTED"
              classification="DUPLICATE"
              resolution="OPEN"
              excessEffectCount={1}
            />
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-text-primary">
            Forced grayscale — silhouette/glyph acceptance test
          </h2>
          <div className="mt-3">
            <StatusMatrix grayscale />
          </div>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-text-primary">Mark</h2>
          <div className="mt-3 flex items-end gap-6 rounded-(--radius-structural) border border-border bg-surface-1 p-5 text-text-primary">
            <SeatMark size={64} standalone />
            <SeatMark size={32} standalone />
            <SeatMark size={24} standalone />
            <SeatMark size={16} standalone />
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-text-primary">Surfaces and text</h2>
          <div className="mt-3 grid grid-cols-4 gap-3">
            {SURFACES.map((surface) => (
              <div
                key={surface}
                className={`rounded-(--radius-structural) border border-border p-3 bg-${surface}`}
              >
                <p className="font-mono text-2xs text-text-tertiary">{surface}</p>
                {TEXT_ROLES.map((role) =>
                  role === "disabled" ? (
                    // Disabled ink is only ever used on inactive controls
                    // (WCAG 1.4.3 exemption); the specimen is one.
                    <button
                      key={role}
                      type="button"
                      disabled
                      className="block p-0 text-left text-sm text-text-disabled"
                    >
                      text-disabled
                    </button>
                  ) : (
                    <p key={role} className={`text-sm text-text-${role}`}>
                      text-{role}
                    </p>
                  ),
                )}
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-text-primary">Type scale</h2>
          <dl className="mt-3 flex flex-col gap-1 rounded-(--radius-structural) border border-border bg-surface-1 p-5">
            {TYPE_SCALE.map(([cls, label]) => (
              <div key={cls} className="flex items-baseline gap-4">
                <dt className="w-20 shrink-0 font-mono text-2xs text-text-tertiary">{cls}</dt>
                <dd className={`${cls} text-text-primary`}>{label}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-text-primary">Controls</h2>
          <div className="mt-3 flex items-center gap-3 rounded-(--radius-structural) border border-border bg-surface-1 p-5">
            <Button>Default</Button>
            <Button variant="accent">Accent</Button>
            <Button variant="ghost">Ghost</Button>
            <Button disabled>Disabled</Button>
            <IconButton label="Copy example">
              <Copy size={14} />
            </IconButton>
          </div>
        </section>
      </div>
    </Page>
  );
}
