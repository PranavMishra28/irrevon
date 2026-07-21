import type { Meta, StoryObj } from "@storybook/react-vite";
import { Copy } from "@/shared/ui/icons";
import { IconButton } from "./button";
import { Layer, Panel, PanelHeader, SunkenWell } from "./panel";

const meta = {
  title: "Primitives/Panel",
  component: Panel,
} satisfies Meta<typeof Panel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PanelWithHeaderGrammar: Story = {
  args: {
    title: "Evidence",
    meta: "3 receipts · as_of 2026-07-21T10:37:48Z",
    actions: (
      <IconButton label="Copy panel contents" onClick={() => undefined}>
        <Copy size={14} />
      </IconButton>
    ),
    children: (
      <p className="max-w-[65ch] text-sm text-text-secondary">
        Panel body content sits on the L3 panel layer. The header grammar is title, mono meta,
        spacer, icon actions; the title never truncates — meta truncates first.
      </p>
    ),
  },
};

export const HeaderOnly: StoryObj = {
  render: () => (
    <div className="rounded-(--radius-structural) border border-border-subtle bg-layer-panel">
      <PanelHeader
        title="Receipts"
        meta="rcpt_01ARZ3… · recorded 2026-07-21T10:28:52Z · dispatcher"
      />
      <div className="p-(--dt-panel-pad) text-sm text-text-secondary">Body</div>
    </div>
  ),
};

export const LayerLadder: StoryObj = {
  render: () => (
    <div className="flex flex-col gap-3 bg-canvas p-4">
      <Layer surface="nav" className="p-3 text-xs text-text-secondary">
        L1 nav — global chrome
      </Layer>
      <Layer surface="workspace" className="p-3 text-xs text-text-secondary">
        L2 workspace — tables, grids, graph stages
        <Layer surface="panel" className="mt-2 p-3">
          L3 panel — evidence panels, inspectors
          <SunkenWell className="mt-2">
            <code className="font-mono text-xs text-text-primary">
              {'{ "sunken": "well — code, raw JSON, empty slots" }'}
            </code>
          </SunkenWell>
        </Layer>
      </Layer>
    </div>
  ),
};

export const SunkenWellScrollsInside: StoryObj = {
  render: () => (
    <SunkenWell scrollX className="max-w-80">
      <pre className="font-mono text-xs text-text-primary">
        {'{"effect_id":"0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5"}'}
      </pre>
    </SunkenWell>
  ),
};
