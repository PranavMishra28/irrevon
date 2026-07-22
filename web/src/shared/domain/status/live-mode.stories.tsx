import type { Meta, StoryObj } from "@storybook/react-vite";
import { DisconnectedBanner, LiveChip, VersionRefusal } from "./live-mode";

/**
 * Live-mode connection chrome. In a live build the top-bar chip is
 * persistent; disconnection escalates to the full-width banner; a
 * schema_version mismatch replaces the entire frame with the refusal.
 */
const meta = {
  title: "Status/LiveMode",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

const FIXED_TIME = new Date("2026-07-21T12:00:00Z").getTime();

export const ChipStates: Story = {
  render: () => (
    <div className="flex flex-col items-start gap-3">
      <LiveChip
        status={{
          state: "connected",
          doctorOk: true,
          failingChecks: 0,
          lastUpdatedAt: FIXED_TIME,
        }}
      />
      <LiveChip
        status={{
          state: "connected",
          doctorOk: false,
          failingChecks: 2,
          lastUpdatedAt: FIXED_TIME,
        }}
      />
      <LiveChip status={{ state: "connecting" }} />
      <LiveChip status={{ state: "disconnected", lastUpdatedAt: FIXED_TIME }} />
    </div>
  ),
};

export const Disconnected: Story = {
  render: () => <DisconnectedBanner />,
};

export const UnsupportedVersion: Story = {
  render: () => <VersionRefusal observed="999" supported="1" />,
};
