import type { Meta, StoryObj } from "@storybook/react-vite";
import effectsFixture from "../../../fixtures/canonical/effects.json";
import flagshipInspect from "../../../fixtures/canonical/inspect/0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5.json";
import ambiguousInspect from "../../../fixtures/canonical/inspect/f18adfccc0bfa6fabc817c15e2afd305a80c5d119f1c7101567cf43f28a913b0.json";
import duplicateInspect from "../../../fixtures/canonical/inspect/efcd86f31233098669466ff0afef22407bb52cb9f557d352685c8e7e785b7954.json";
import type { EffectRecord } from "@/shared/contracts/generated/effect-record";
import type { InspectPayload } from "@/shared/api/types";
import {
  AttemptsSection,
  DecisionLogSection,
  IdentitySection,
  RawJsonSection,
  ReconciliationSection,
  ResynthesisSection,
} from "./evidence";
import { EffectTimeline } from "./timeline";

/**
 * Story args are the captured real-engine transcripts (fixtures/canonical);
 * nothing here is hand-shaped.
 */

const flagship = flagshipInspect as unknown as InspectPayload;
const ambiguous = ambiguousInspect as unknown as InspectPayload;
const duplicate = duplicateInspect as unknown as InspectPayload;
const flagshipRecord = (effectsFixture.data as unknown as EffectRecord[]).find(
  (r) => r.effect_id === flagship.record.effect_id,
);

const meta = {
  title: "Investigation/EffectDetail",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const TimelineFlagship: Story = {
  render: () => (
    <div className="max-w-md">
      <EffectTimeline payload={flagship} />
    </div>
  ),
};

export const TimelineAmbiguousOpen: Story = {
  render: () => (
    <div className="max-w-md">
      <EffectTimeline payload={ambiguous} />
    </div>
  ),
};

export const Identity: Story = {
  render: () => (
    <div className="max-w-xl">
      <IdentitySection payload={flagship} record={flagshipRecord} />
    </div>
  ),
};

export const Attempts: Story = {
  render: () => (
    <div className="max-w-xl">
      <AttemptsSection payload={flagship} />
    </div>
  ),
};

export const ReconciliationClosed: Story = {
  render: () => (
    <div className="max-w-xl">
      <ReconciliationSection payload={flagship} />
    </div>
  ),
};

export const ReconciliationDuplicateOpen: Story = {
  render: () => (
    <div className="max-w-xl">
      <ReconciliationSection payload={duplicate} />
    </div>
  ),
};

export const ResynthesisExhibit: Story = {
  render: () => (
    <div className="max-w-xl">
      <ResynthesisSection payload={flagship} record={flagshipRecord} />
    </div>
  ),
};

export const DecisionLog: Story = {
  render: () => (
    <div className="max-w-xl">
      <DecisionLogSection payload={flagship} />
    </div>
  ),
};

export const RawJson: Story = {
  render: () => (
    <div className="max-w-xl">
      <RawJsonSection payload={flagship} />
    </div>
  ),
};
