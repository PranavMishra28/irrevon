import type { Meta, StoryObj } from "@storybook/react-vite";
import { LifecyclePill } from "@/shared/domain/status/lifecycle-pill";
import { FindingBadge } from "@/shared/domain/status/finding-badge";
import { ResolutionTag } from "@/shared/domain/status/resolution-tag";
import { RecordCard } from "./record-card";

const meta = {
  title: "Primitives/RecordCard",
  component: RecordCard,
} satisfies Meta<typeof RecordCard>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Values below come from the canonical flagship fixture (seed 777). */
const statuses = (
  <dl className="grid grid-cols-[max-content_1fr] items-center gap-x-3 gap-y-1">
    <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">Lifecycle</dt>
    <dd>
      <LifecyclePill value="SETTLED_COMMITTED" />
    </dd>
    <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
      Reconciliation
    </dt>
    <dd>
      <FindingBadge value="CONFIRMED_UNIQUE" />
    </dd>
    <dt className="font-mono text-2xs tracking-wide text-text-tertiary uppercase">
      Resolution
    </dt>
    <dd>
      <ResolutionTag value="CLOSED" />
    </dd>
  </dl>
);

export const EffectCard: Story = {
  args: {
    heading: "0bb7e8d64711… · order.create",
    headingId: "record-card-story-heading",
    meta: "IRREVERSIBLE",
    fields: [
      { label: "Scope", value: "acme-store/prod" },
      { label: "Adapter", value: "refdest-c2" },
    ],
    statuses,
  },
  render: (args) => (
    <div className="max-w-96 bg-layer-workspace p-4">
      <RecordCard {...args} />
    </div>
  ),
};

export const InspectedCard: Story = {
  args: {
    heading: "0bb7e8d64711… · order.create",
    headingId: "record-card-story-inspected",
    fields: [{ label: "Scope", value: "acme-store/prod" }],
    statuses,
    inspected: true,
  },
  render: (args) => (
    <div className="max-w-96 bg-layer-workspace p-6">
      <RecordCard {...args} />
    </div>
  ),
};
