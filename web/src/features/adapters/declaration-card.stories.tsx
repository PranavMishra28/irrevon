import type { Meta, StoryObj } from "@storybook/react-vite";
import adaptersFixture from "../../../fixtures/canonical/adapters.json";
import type { CapabilityDeclaration } from "@/shared/contracts/generated/capability-declaration";
import { DeclarationCard } from "./declaration-card";

const declaration = (adaptersFixture.data as CapabilityDeclaration[])[0];
if (!declaration) throw new Error("adapters fixture is empty");

const meta = {
  title: "Adapters/DeclarationCard",
  component: DeclarationCard,
} satisfies Meta<typeof DeclarationCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const RefdestC2: Story = { args: { declaration } };
