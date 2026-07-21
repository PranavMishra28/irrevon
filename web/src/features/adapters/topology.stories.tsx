import type { Meta, StoryObj } from "@storybook/react-vite";
import adaptersFixture from "../../../fixtures/canonical/adapters.json";
import healthFixture from "../../../fixtures/canonical/health.json";
import type { CapabilityDeclaration } from "@/shared/contracts/generated/capability-declaration";
import { DoctorSummaryGrid } from "@/features/overview/modules";
import { summarizeDoctor } from "@/features/overview/aggregate";
import { AdapterTopology } from "./topology";

const declarations = (adaptersFixture as { data: unknown }).data as CapabilityDeclaration[];

const meta = {
  title: "Adapters/Topology",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const DeclaredTopology: Story = {
  render: () => (
    <div className="max-w-4xl">
      <AdapterTopology declarations={declarations} />
    </div>
  ),
};

export const VerticalTopology: Story = {
  render: () => (
    <div className="max-w-90">
      <AdapterTopology declarations={declarations} vertical />
    </div>
  ),
};

export const NoDeclarations: Story = {
  render: () => (
    <div className="max-w-lg">
      <AdapterTopology declarations={[]} />
    </div>
  ),
};

export const DoctorSummary: Story = {
  render: () => (
    <div className="max-w-60">
      <DoctorSummaryGrid
        summary={summarizeDoctor((healthFixture as { checks: { status: string }[] }).checks)}
      />
    </div>
  ),
};

export const DoctorSummaryWithFailures: Story = {
  render: () => (
    <div className="max-w-60">
      {/* UI-state exhibit: not a captured transcript. */}
      <DoctorSummaryGrid summary={{ ok: 4, warn: 2, fail: 1, other: 0 }} />
    </div>
  ),
};
