import type { Meta, StoryObj } from "@storybook/react-vite";
import { CommandDialog, type PaletteCommand } from "./command-dialog";

const COMMANDS: readonly PaletteCommand[] = [
  { id: "/effects", label: "Effects", hint: "g e" },
  { id: "/demo", label: "Demo", hint: "g d" },
  { id: "/health", label: "Health", hint: "g h" },
  {
    id: "receipt",
    label: "Receipt rcpt_01ARZ3…",
    disabled: true,
    disabledReason: "no receipt route in v0.1",
  },
];

const meta = {
  title: "Primitives/CommandDialog",
  component: CommandDialog,
  args: {
    open: true,
    onOpenChange: () => undefined,
    commands: COMMANDS,
    resolveExact: (_input: string): PaletteCommand | null => null,
    onSelect: () => undefined,
    placeholder: "Go to view, or paste an exact id",
  },
} satisfies Meta<typeof CommandDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Open: Story = {};

export const ExactIdMatch: Story = {
  args: {
    resolveExact: (input: string) =>
      input.trim() === ""
        ? null
        : { id: "/effects/abc", label: "Open effect abcdefabcdef…", hint: "exact id" },
  },
};
