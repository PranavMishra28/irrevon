import type { Meta, StoryObj } from "@storybook/react-vite";
import { ContractPendingState, Page } from "./page";

const meta = {
  title: "Layout/Page",
  component: Page,
} satisfies Meta<typeof Page>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithLead: Story = {
  args: {
    title: "Effects",
    lead: "Every registered effect record: identity, lifecycle, reconciliation classification, and resolution.",
  },
};

export const ContractPending: Story = {
  args: {
    title: "Findings",
    lead: "Reconciliation verdicts, including destination-keyed orphans.",
    children: (
      <ContractPendingState
        what="Findings render from the corrected ReconciliationFinding / Q2 envelope schemas."
        blockedOn="BI-2, BI-3, BI-8"
      />
    ),
  },
};
