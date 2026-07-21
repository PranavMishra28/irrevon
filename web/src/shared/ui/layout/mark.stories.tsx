import type { Meta, StoryObj } from "@storybook/react-vite";
import { SeatMark } from "./mark";

const meta = {
  title: "Layout/SeatMark",
  component: SeatMark,
} satisfies Meta<typeof SeatMark>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Standalone: Story = {
  args: { size: 48, standalone: true },
};

export const AtSixteenPixels: Story = {
  args: { size: 16, standalone: true },
};

export const DecorativeWithWordmark: Story = {
  render: () => (
    <span className="flex items-center gap-2 text-text-primary">
      <SeatMark size={18} />
      <span className="text-sm font-semibold">irrevon</span>
    </span>
  ),
};
