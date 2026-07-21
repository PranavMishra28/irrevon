import type { Meta, StoryObj } from "@storybook/react-vite";
import { Copy } from "@/shared/ui/icons";
import { Button, IconButton } from "./button";

const meta = {
  title: "Primitives/Button",
  component: Button,
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { args: { children: "Refresh" } };
export const Accent: Story = { args: { children: "Play the demo", variant: "accent" } };
export const Ghost: Story = { args: { children: "Clear filters", variant: "ghost" } };
export const Disabled: Story = { args: { children: "Unavailable", disabled: true } };

export const IconOnly: Story = {
  render: () => (
    <IconButton label="Copy effect id">
      <Copy size={14} />
    </IconButton>
  ),
};
