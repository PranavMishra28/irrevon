import type { Meta, StoryObj } from "@storybook/react-vite";
import { AppFrame, DataModeBanner } from "./app-frame";

const meta = {
  title: "Layout/AppFrame",
  component: AppFrame,
} satisfies Meta<typeof AppFrame>;

export default meta;
type Story = StoryObj<typeof meta>;

const navItems = ["Effects", "Findings", "Attention", "Demo", "Learn", "Health"].map(
  (label, index) => (
    <a
      key={label}
      href="#main"
      data-status={index === 0 ? "active" : undefined}
      className={
        "relative flex items-center border-b-2 border-transparent px-2.5 text-sm " +
        "text-text-secondary hover:text-text-primary " +
        "data-[status=active]:border-(--color-accent) data-[status=active]:font-medium " +
        "data-[status=active]:text-text-primary"
      }
    >
      {label}
    </a>
  ),
);

export const MockMode: Story = {
  args: {
    banner: <DataModeBanner>Synthetic fixture — not live or measured</DataModeBanner>,
    nav: navItems,
    utilities: <span className="text-xs text-text-tertiary">utilities</span>,
    children: <div className="p-6 text-sm text-text-primary">Route content</div>,
  },
};

export const LiveMode: Story = {
  args: {
    nav: navItems,
    utilities: <span className="text-xs text-text-tertiary">utilities</span>,
    children: <div className="p-6 text-sm text-text-primary">Route content</div>,
  },
};
