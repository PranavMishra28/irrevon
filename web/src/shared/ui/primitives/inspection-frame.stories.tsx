import type { Meta, StoryObj } from "@storybook/react-vite";
import { InspectionFrame, InspectionSeatBar } from "./inspection-frame";

const meta = {
  title: "Primitives/InspectionFrame",
  component: InspectionFrame,
} satisfies Meta<typeof InspectionFrame>;

export default meta;
type Story = StoryObj<typeof meta>;

const card = (
  <div className="rounded-(--radius-structural) border border-border-subtle bg-layer-panel p-4">
    <p className="font-mono text-xs text-text-primary">0bb7e8d64711…</p>
    <p className="mt-1 text-sm text-text-secondary">order.create · acme-store/prod</p>
  </div>
);

export const Inspected: Story = {
  args: { inspected: true, children: card },
  render: (args) => (
    <div className="bg-layer-workspace p-8">
      <InspectionFrame {...args} />
    </div>
  ),
};

export const NotInspected: Story = {
  args: { inspected: false, children: card },
  render: (args) => (
    <div className="bg-layer-workspace p-8">
      <InspectionFrame {...args} />
    </div>
  ),
};

export const DenseRowSeatBar: StoryObj = {
  render: () => (
    <table className="w-96 border-collapse bg-layer-workspace">
      <tbody>
        <tr className="h-(--dt-row-h) border-b border-border-subtle">
          <td className="relative px-3 font-mono text-xs text-text-primary">
            <InspectionSeatBar />
            0bb7e8d64711…
          </td>
          <td className="px-3 text-sm text-text-secondary">selected row</td>
        </tr>
        <tr className="h-(--dt-row-h) border-b border-border-subtle">
          <td className="px-3 font-mono text-xs text-text-primary">c85c01dc4fe6…</td>
          <td className="px-3 text-sm text-text-secondary">unselected row</td>
        </tr>
      </tbody>
    </table>
  ),
};
