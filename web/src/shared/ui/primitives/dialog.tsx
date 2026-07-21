import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import type { ReactNode } from "react";

/**
 * Styled modal dialog over Base UI. One overlay shadow token; borders carry
 * the boundary; focus is trapped and restored by Base UI.
 */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  wide = false,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <BaseDialog.Root open={open} onOpenChange={onOpenChange}>
      <BaseDialog.Portal>
        <BaseDialog.Backdrop className="fixed inset-0 z-(--sys-z-overlay) bg-canvas/60" />
        <BaseDialog.Popup
          className={
            "fixed top-[15vh] left-1/2 z-(--sys-z-modal) w-full -translate-x-1/2 " +
            (wide ? "max-w-2xl " : "max-w-lg ") +
            "rounded-(--radius-structural) border border-border-strong bg-surface-1 " +
            "shadow-overlay outline-none"
          }
        >
          <div className="border-b border-border-subtle px-4 py-3">
            <BaseDialog.Title className="text-lg font-semibold text-text-primary">
              {title}
            </BaseDialog.Title>
            {description ? (
              <BaseDialog.Description className="mt-0.5 text-sm text-text-secondary">
                {description}
              </BaseDialog.Description>
            ) : null}
          </div>
          <div className="px-4 py-3">{children}</div>
        </BaseDialog.Popup>
      </BaseDialog.Portal>
    </BaseDialog.Root>
  );
}
