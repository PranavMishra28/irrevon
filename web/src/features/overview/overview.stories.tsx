import type { Meta, StoryObj } from "@storybook/react-vite";
import effectsFixture from "../../../fixtures/canonical/effects.json";
import findingsFixture from "../../../fixtures/canonical/findings.json";
import type { EffectRecord } from "@/shared/contracts/generated/effect-record";
import type { EffectsEnvelope, FindingsEnvelope } from "@/shared/api/types";
import { aggregateEffects } from "./aggregate";
import {
  ConceptualArchitecture,
  DistributionModule,
  ModuleError,
  ModuleSkeleton,
  SourceFreshnessBar,
  SourceStamp,
} from "./modules";

/** Counts below are aggregated from the canonical fixture envelope. */
const records = (effectsFixture as { data: unknown }).data as EffectRecord[];
const findings = (findingsFixture as unknown as FindingsEnvelope).data;
const envelope: EffectsEnvelope = {
  schema_version: "1",
  data: records.map((record) => {
    const finding =
      findings.find(
        (f) => "effect_id" in f.subject && f.subject.effect_id === record.effect_id,
      ) ?? null;
    return {
      record,
      classification: finding ? finding.classification : "UNRECONCILED",
      finding,
    };
  }),
  has_more: false,
  next_cursor: null,
  as_of: (effectsFixture as { as_of: string }).as_of,
};
const agg = aggregateEffects(envelope);

const meta = {
  title: "Overview/Modules",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const LifecycleDistribution: Story = {
  render: () => (
    <div className="max-w-sm">
      <DistributionModule
        title="Effects by lifecycle"
        rows={agg.byLifecycle}
        total={agg.total}
        complete={agg.complete}
        emptyText="No recorded effects."
      />
    </div>
  ),
};

export const PartialSnapshotRefusal: Story = {
  render: () => (
    <div className="max-w-sm">
      <DistributionModule
        title="Effects by lifecycle"
        rows={[]}
        total={3}
        complete={false}
        emptyText="No recorded effects."
      />
    </div>
  ),
};

export const SourceError: Story = {
  render: () => (
    <div className="max-w-sm">
      <ModuleError title="Effects by adapter" message="TransportError: 503 /api/v1/effects" />
    </div>
  ),
};

export const Skeleton: Story = {
  render: () => (
    <div className="max-w-sm">
      <ModuleSkeleton title="Effects by lifecycle" visible />
    </div>
  ),
};

export const Architecture: Story = {
  render: () => (
    <div className="max-w-4xl">
      <ConceptualArchitecture />
    </div>
  ),
};

export const Freshness: Story = {
  render: () => (
    <SourceFreshnessBar>
      <SourceStamp name="effects as_of" asOf={envelope.as_of} />
      <SourceStamp name="findings as_of" asOf={envelope.as_of} />
      <SourceStamp name="adapters as_of" asOf={undefined} />
    </SourceFreshnessBar>
  ),
};
