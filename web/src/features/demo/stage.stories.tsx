import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import demoArtifact from "../../../fixtures/canonical/demo-artifact.json";
import type { DemoArtifact } from "@/shared/api/types";
import { ContrastSummary, DemoStage, type Lane } from "./stage";

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

function StageDemo({ initialStep, a }: { initialStep: number; a: DemoArtifact }) {
  const [step, setStep] = useState(initialStep);
  const [lane, setLane] = useState<Lane>("both");
  return (
    <DemoStage
      artifact={a}
      step={step}
      lane={lane}
      onStepChange={setStep}
      onLaneChange={setLane}
    />
  );
}

const meta = {
  title: "Demo/Stage",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Idle: Story = { render: () => <StageDemo initialStep={0} a={artifact} /> };

export const MidRun: Story = { render: () => <StageDemo initialStep={4} a={artifact} /> };

export const CompleteHolds: Story = {
  render: () => <StageDemo initialStep={artifact.events.length - 1} a={artifact} />,
};

export const CompleteDoesNotHold: Story = {
  render: () => <StageDemo initialStep={failedArtifact.events.length - 1} a={failedArtifact} />,
  name: "Complete (contrast failed — falsification exhibit)",
};

export const ContrastHolds: Story = {
  render: () => <ContrastSummary artifact={artifact} />,
};
