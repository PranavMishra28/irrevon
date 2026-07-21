import type { Meta, StoryObj } from "@storybook/react-vite";
import demoArtifact from "../../../fixtures/canonical/demo-artifact.json";
import type { DemoArtifact } from "@/shared/api/types";
import { ContrastSummary } from "./player";

const artifact = demoArtifact as unknown as DemoArtifact;

/** The failed-contrast variant is a UI-state exhibit (state matrix row
 * "Demo contrast failed"), clearly not a captured result. */
const failedArtifact: DemoArtifact = {
  ...artifact,
  summary: {
    ...artifact.summary,
    b5_leg: { destination_effects: 1, duplicate_created: false },
    contrast_holds: false,
  },
};

const meta = {
  title: "Demo/ContrastSummary",
  component: ContrastSummary,
} satisfies Meta<typeof ContrastSummary>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Holds: Story = { args: { artifact } };

export const Failed: Story = {
  args: { artifact: failedArtifact },
  name: "Failed (falsification state exhibit)",
};
