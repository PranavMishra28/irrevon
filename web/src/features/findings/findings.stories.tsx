import type { Meta, StoryObj } from "@storybook/react-vite";
import findingsFixture from "../../../fixtures/canonical/findings.json";
import type { FindingsEnvelope } from "@/shared/api/types";
import { FindingInspector, OrphanPairedView } from "./inspector";

/** All finding payloads are the canonical captured fixtures (seed 777). */
const findings = (findingsFixture as unknown as FindingsEnvelope).data;
const effectBacked = findings.find((f) => "effect_id" in f.subject);
const orphan = findings.find((f) => !("effect_id" in f.subject));

const meta = {
  title: "Findings/Inspector",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const EffectBacked: Story = {
  render: () =>
    effectBacked ? (
      <div className="max-w-md">
        <FindingInspector finding={effectBacked} onClose={() => undefined} />
      </div>
    ) : (
      <p>fixture missing</p>
    ),
};

export const DestinationKeyedOrphan: Story = {
  render: () =>
    orphan ? (
      <div className="max-w-md">
        <FindingInspector finding={orphan} onClose={() => undefined} />
      </div>
    ) : (
      <p>fixture missing</p>
    ),
};

export const OrphanPairOnly: Story = {
  render: () =>
    orphan ? (
      <div className="max-w-lg">
        <OrphanPairedView finding={orphan} />
      </div>
    ) : (
      <p>fixture missing</p>
    ),
};
