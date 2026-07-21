import type { Meta, StoryObj } from "@storybook/react-vite";
import {
  ContrastFailedNotice,
  DoctorCheckStatus,
  GateCheckChip,
  GateOutcomeText,
  IntegrityLine,
} from "./verdicts";

const meta = {
  title: "Status/Verdicts",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const DoctorStatuses: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <DoctorCheckStatus value="ok" />
      <DoctorCheckStatus value="warn" />
      <DoctorCheckStatus value="fail" />
      <DoctorCheckStatus value="mystery" />
    </div>
  ),
};

export const GateOutcomes: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <GateOutcomeText value="ALLOW" />
        <GateOutcomeText value="DENY" />
      </div>
      <div className="flex flex-wrap gap-1.5">
        <GateCheckChip check="deny_list" status="passed" />
        <GateCheckChip check="authority" status="passed" />
        <GateCheckChip check="branch_lineage" status="passed" />
        <GateCheckChip check="dedup" status="denied" />
      </div>
    </div>
  ),
};

export const Integrity: Story = {
  render: () => (
    <div className="flex flex-col gap-2">
      <IntegrityLine matches />
      <IntegrityLine matches={false} />
      <ContrastFailedNotice />
    </div>
  ),
};
