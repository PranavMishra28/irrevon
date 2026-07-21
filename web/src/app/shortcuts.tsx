import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { getSingleKeyShortcutsEnabled, setSingleKeyShortcutsEnabled } from "@/shared/lib/prefs";
import { Kbd } from "@/shared/ui/primitives/command-dialog";
import { Dialog } from "@/shared/ui/primitives/dialog";

/**
 * Global keyboard contract (BRIEF §10). Single-character shortcuts are
 * user-disableable, never fire inside inputs/contenteditable, and every
 * shortcut is redundant with a visible control.
 */

const GO_TARGETS: Record<string, string> = {
  e: "/effects",
  d: "/demo",
  h: "/health",
  b: "/bench",
};

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
}

export function useGlobalShortcuts({
  onOpenPalette,
  onOpenHelp,
}: {
  onOpenPalette: () => void;
  onOpenHelp: () => void;
}) {
  const navigate = useNavigate();
  const pendingG = useRef(false);
  const pendingTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const mod = event.metaKey || event.ctrlKey;

      if (mod && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenPalette();
        return;
      }
      if (mod && event.key === "/") {
        event.preventDefault();
        onOpenHelp();
        return;
      }

      if (mod || event.altKey || isEditableTarget(event.target)) return;
      if (!getSingleKeyShortcutsEnabled()) return;

      if (event.key === "?") {
        event.preventDefault();
        onOpenHelp();
        return;
      }

      if (pendingG.current) {
        pendingG.current = false;
        clearTimeout(pendingTimer.current);
        const to = GO_TARGETS[event.key.toLowerCase()];
        if (to) {
          event.preventDefault();
          void navigate({ to });
        }
        return;
      }

      if (event.key === "g") {
        pendingG.current = true;
        clearTimeout(pendingTimer.current);
        pendingTimer.current = setTimeout(() => {
          pendingG.current = false;
        }, 1500);
      }
    };

    window.addEventListener("keydown", handler);
    return () => {
      window.removeEventListener("keydown", handler);
      clearTimeout(pendingTimer.current);
    };
  }, [navigate, onOpenPalette, onOpenHelp]);
}

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
