import type { Meta, StoryObj } from "@storybook/react-vite";
import {
  CLASSIFICATIONS,
  EFFECT_CLASSES,
  LIFECYCLE_STATES,
  RESOLUTION_STATUSES,
  TRANSPORT_OUTCOMES,
} from "@/shared/contracts/generated/state-model";
import { FindingBadge } from "./finding-badge";
import { LifecyclePill } from "./lifecycle-pill";
import { ResolutionNotApplicable, ResolutionTag } from "./resolution-tag";
import { StatusTriplet } from "./status-triplet";
import {
  EffectClassBadge,
  EvidenceQualityTag,
  TierMeter,
  TransportOutcomeInline,
} from "./supporting-status";
import { UnknownStatus } from "./unknown-status";

const meta = {
  title: "Status/Taxonomy",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const row = "flex flex-wrap items-center gap-2";

export const LifecycleAll: Story = {
  render: () => (
    <div className={row}>
      {LIFECYCLE_STATES.map((v) => (
        <LifecyclePill key={v} value={v} />
      ))}
    </div>
  ),
};

export const ClassificationAll: Story = {
  render: () => (
    <div className={row}>
      <FindingBadge value="UNRECONCILED" />
      {CLASSIFICATIONS.map((v) =>
        v === "DUPLICATE" ? (
          <FindingBadge key={v} value={v} excessEffectCount={2} />
        ) : (
          <FindingBadge key={v} value={v} />
        ),
      )}
    </div>
  ),
};

export const ResolutionAll: Story = {
  render: () => (
    <div className={row}>
      {RESOLUTION_STATUSES.map((v) => (
        <ResolutionTag key={v} value={v} />
      ))}
      <ResolutionNotApplicable />
    </div>
  ),
};

export const SupportingAll: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
      <div className={row}>
        {EFFECT_CLASSES.map((v) => (
          <EffectClassBadge key={v} value={v} />
        ))}
      </div>
      <div className={row}>
        {TRANSPORT_OUTCOMES.map((v) => (
          <TransportOutcomeInline key={v} value={v} />
        ))}
      </div>
      <div className={row}>
        <TierMeter value="C1" />
        <TierMeter value="C2" />
        <TierMeter value="C3" />
        <EvidenceQualityTag value="VF" />
        <EvidenceQualityTag value="EI" />
      </div>
    </div>
  ),
};

export const Triplet: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
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
  ),
};

export const UnknownGuard: Story = {
  render: () => (
    <div className={row}>
      <UnknownStatus dimension="lifecycle" value="NOT_A_STATE" />
      <LifecyclePill value="NOT_A_STATE" />
      <FindingBadge value="MYSTERY" />
    </div>
  ),
};

export const ForcedGrayscale: Story = {
  render: () => (
    <div className="flex flex-col gap-3" style={{ filter: "grayscale(1)" }}>
      <div className={row}>
        {LIFECYCLE_STATES.map((v) => (
          <LifecyclePill key={v} value={v} />
        ))}
      </div>
      <div className={row}>
        <FindingBadge value="UNRECONCILED" />
        {CLASSIFICATIONS.map((v) =>
          v === "DUPLICATE" ? (
            <FindingBadge key={v} value={v} excessEffectCount={2} />
          ) : (
            <FindingBadge key={v} value={v} />
          ),
        )}
      </div>
      <div className={row}>
        {RESOLUTION_STATUSES.map((v) => (
          <ResolutionTag key={v} value={v} />
        ))}
      </div>
    </div>
  ),
  parameters: {
    // Contrast is asserted on the colored variants; the grayscale story is a
    // silhouette/glyph distinguishability exhibit.
    a11y: { config: { rules: [{ id: "color-contrast", enabled: false }] } },
  },
};
