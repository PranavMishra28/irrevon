import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import flagshipInspect from "../../../fixtures/canonical/inspect/0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5.json";
import persistedInspect from "../../../fixtures/canonical/inspect/371a59b8452dd4fe659e9dd4ef78fd8cac90b5dd36583aea1dff9e99b4f74f6c.json";
import ambiguousInspect from "../../../fixtures/canonical/inspect/f18adfccc0bfa6fabc817c15e2afd305a80c5d119f1c7101567cf43f28a913b0.json";
import lostInspect from "../../../fixtures/canonical/inspect/c85c01dc4fe6fd581e7b528ac1baacc59490e5d195f3a16c427e3ee516214817.json";
import duplicateInspect from "../../../fixtures/canonical/inspect/efcd86f31233098669466ff0afef22407bb52cb9f557d352685c8e7e785b7954.json";
import type { InspectPayload } from "@/shared/api/types";
import { buildEffectGraph } from "./model";
import { CausalGraph } from "./renderer";
import { GraphLegend } from "./legend";
import { ConnectionsTable } from "./connections";
import { GraphNodeInspector, type InspectorPanel } from "./inspector";

/** Every payload below is a canonical captured engine transcript (seed 777). */
const flagship = buildEffectGraph({ inspect: flagshipInspect as unknown as InspectPayload });
const persisted = buildEffectGraph({ inspect: persistedInspect as unknown as InspectPayload });
const ambiguous = buildEffectGraph({ inspect: ambiguousInspect as unknown as InspectPayload });
const lost = buildEffectGraph({ inspect: lostInspect as unknown as InspectPayload });
const duplicate = buildEffectGraph({ inspect: duplicateInspect as unknown as InspectPayload });

const integrityFailed = buildEffectGraph({
  inspect: {
    ...(flagshipInspect as unknown as InspectPayload),
    integrity: { recomputed_intent_id: "f".repeat(64), matches: false },
  },
});

const unknownEnum = buildEffectGraph({
  inspect: {
    ...(ambiguousInspect as unknown as InspectPayload),
    record: {
      ...(ambiguousInspect as unknown as InspectPayload).record,
      lifecycle: "NOT_A_STATE",
    },
  },
});

function InteractiveGraph({ model }: { model: typeof flagship }) {
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <div className="bg-layer-workspace p-4">
      <CausalGraph
        model={model}
        orientation="horizontal"
        selected={selected}
        onSelect={setSelected}
      />
    </div>
  );
}

const meta = {
  title: "Graph/CausalGraph",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Flagship: Story = { render: () => <InteractiveGraph model={flagship} /> };
export const PersistedNoNotch: Story = { render: () => <InteractiveGraph model={persisted} /> };
export const AmbiguousUnknownSlot: Story = {
  render: () => <InteractiveGraph model={ambiguous} />,
};
export const LostConfirmedAbsence: Story = { render: () => <InteractiveGraph model={lost} /> };
export const DuplicateObservedExcess: Story = {
  render: () => <InteractiveGraph model={duplicate} />,
};
export const IntegrityFailed: Story = {
  render: () => <InteractiveGraph model={integrityFailed} />,
};
export const UnknownEnumValues: Story = {
  render: () => <InteractiveGraph model={unknownEnum} />,
};

export const VerticalFlagship: Story = {
  render: () => (
    <div className="max-w-90 bg-layer-workspace p-2">
      <CausalGraph
        model={flagship}
        orientation="vertical"
        selected={null}
        onSelect={() => undefined}
      />
    </div>
  ),
};

export const Legend: Story = {
  render: () => (
    <div className="max-w-md">
      <GraphLegend />
    </div>
  ),
};

export const Connections: Story = {
  render: () => (
    <div className="max-w-3xl">
      <ConnectionsTable model={flagship} />
    </div>
  ),
};

function InspectorDemo() {
  const [panel, setPanel] = useState<InspectorPanel>("summary");
  const node = flagship.nodes.find((n) => n.kind === "attempt");
  if (!node) return <p>fixture missing</p>;
  return (
    <div className="max-w-sm">
      <GraphNodeInspector
        model={flagship}
        node={node}
        panel={panel}
        onPanelChange={setPanel}
        onClose={() => undefined}
      />
    </div>
  );
}

export const EvidenceInspector: Story = { render: () => <InspectorDemo /> };
