import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import { useRef } from "react";
import type { ReactNode } from "react";
import { X } from "@/shared/ui/icons";

/**
 * The tablet/mobile navigation drawer (REDESIGN-BRIEF §1 A6): a Base UI
 * Dialog fixed to the right, width min(320px, 100vw − 24px), full height,
 * overlay + locked body scroll. Initial focus goes to Close; Tab is trapped;
 * Escape/backdrop close; closing without navigation returns focus to the
 * trigger. Loaded on first use — never part of the initial route JS.
 */
export function MobileNavDialog({
  open,
  onOpenChange,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);

  return (
    <BaseDialog.Root open={open} onOpenChange={onOpenChange}>
      <BaseDialog.Portal>
        <BaseDialog.Backdrop className="fixed inset-0 z-(--sys-z-overlay) bg-canvas/60" />
        <BaseDialog.Popup
          initialFocus={closeRef}
          aria-label="Menu"
          className={
            "fixed inset-y-0 right-0 z-(--sys-z-modal) flex h-full " +
            "w-[min(320px,calc(100vw-24px))] flex-col border-l border-border " +
            "bg-layer-overlay shadow-overlay outline-none " +
            "transition-transform duration-(--sys-dur-slow) ease-(--sys-ease-out) " +
            "data-[ending-style]:translate-x-full data-[ending-style]:duration-(--sys-dur-base) " +
            "data-[ending-style]:ease-(--sys-ease-in) data-[starting-style]:translate-x-full"
          }
        >
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-border-subtle pr-2 pl-4">
            <BaseDialog.Title className="text-sm font-semibold text-text-primary">
              Menu
            </BaseDialog.Title>
            <BaseDialog.Close
              ref={closeRef}
              aria-label="Close menu"
              className={
                "inline-flex size-11 items-center justify-center rounded-(--radius-control) " +
                "text-text-secondary hover:bg-(--sys-state-hover) hover:text-text-primary"
              }
            >
              <X size={16} />
            </BaseDialog.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto py-2">{children}</div>
        </BaseDialog.Popup>
      </BaseDialog.Portal>
    </BaseDialog.Root>
  );
}
