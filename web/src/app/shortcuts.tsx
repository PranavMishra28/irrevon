import { useNavigate } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { getSingleKeyShortcutsEnabled } from "@/shared/lib/prefs";

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
