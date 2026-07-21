import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { Button } from "@/shared/ui/primitives/button";
import { MobileNavDialog } from "./mobile-nav";

const meta = {
  title: "Layout/MobileNavDialog",
  component: MobileNavDialog,
} satisfies Meta<typeof MobileNavDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

const ROW =
  "flex min-h-11 w-full items-center gap-3 px-4 text-left text-sm " +
  "text-text-secondary hover:bg-(--sys-state-hover) hover:text-text-primary";

function DrawerDemo() {
  const [open, setOpen] = useState(true);
  return (
    <div className="min-h-96">
      <Button
        onClick={() => {
          setOpen(true);
        }}
      >
        Open menu
      </Button>
      <MobileNavDialog open={open} onOpenChange={setOpen}>
        <nav aria-label="Views">
          <ul>
            {["Overview", "Effects", "Findings", "Attention", "Health"].map((label, index) => (
              <li key={label}>
                <a
                  href="#main"
                  aria-current={index === 0 ? "page" : undefined}
                  className={
                    ROW +
                    (index === 0
                      ? " border-l-2 border-(--color-accent) font-medium text-text-primary"
                      : "")
                  }
                >
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </MobileNavDialog>
    </div>
  );
}

export const Open: Story = {
  args: { open: true, onOpenChange: () => undefined, children: null },
  render: () => <DrawerDemo />,
};
