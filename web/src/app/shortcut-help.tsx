import { useState } from "react";
import { getSingleKeyShortcutsEnabled, setSingleKeyShortcutsEnabled } from "@/shared/lib/prefs";
import { Kbd } from "@/shared/ui/primitives/command-dialog";
import { Dialog } from "@/shared/ui/primitives/dialog";

/**
 * Shortcut help dialog — lazy-loaded on first use so the dialog machinery
 * never rides in the initial route JS (REDESIGN-BRIEF A3).
 */

const SHORTCUT_ROWS: readonly { keys: readonly string[]; action: string }[] = [
  { keys: ["⌘", "K"], action: "Open command palette / exact-id router" },
  { keys: ["⌘", "/"], action: "Open this shortcut help" },
  { keys: ["?"], action: "Open this shortcut help" },
  { keys: ["g", "e"], action: "Go to Effects" },
  { keys: ["g", "d"], action: "Go to Demo" },
  { keys: ["g", "h"], action: "Go to Health" },
  { keys: ["g", "b"], action: "Go to Benchmark" },
  { keys: ["Esc"], action: "Close topmost dialog; restore invoking focus" },
  { keys: ["↑ ↓", "j k"], action: "Move row focus (effects grid)" },
  { keys: ["→ ←"], action: "Enter / leave cell navigation (effects grid)" },
  { keys: ["Enter", "o"], action: "Open focused effect" },
  { keys: ["c"], action: "Copy focused effect id" },
  { keys: ["/"], action: "Focus filters (effects grid)" },
];

export function ShortcutHelpDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [singleKeys, setSingleKeys] = useState(getSingleKeyShortcutsEnabled);

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Keyboard shortcuts"
      description="Single-character shortcuts never fire while typing in a field."
    >
      <ul className="flex flex-col divide-y divide-border-subtle">
        {SHORTCUT_ROWS.map((row) => (
          <li key={row.action} className="flex items-center justify-between gap-4 py-1.5">
            <span className="text-sm text-text-primary">{row.action}</span>
            <span className="flex shrink-0 items-center gap-1">
              {row.keys.map((k) => (
                <Kbd key={k}>{k}</Kbd>
              ))}
            </span>
          </li>
        ))}
      </ul>
      <label className="mt-3 flex items-center gap-2 border-t border-border-subtle pt-3 text-sm text-text-primary">
        <input
          type="checkbox"
          checked={singleKeys}
          onChange={(event) => {
            setSingleKeys(event.target.checked);
            setSingleKeyShortcutsEnabled(event.target.checked);
          }}
          className="size-4 accent-(--color-accent)"
        />
        Enable single-character shortcuts (g, ?, j/k, o, c, /)
      </label>
    </Dialog>
  );
}
