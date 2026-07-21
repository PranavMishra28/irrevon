import { Autocomplete } from "@base-ui/react/autocomplete";
import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";

/**
 * Domain-blind command palette primitive: Base UI Autocomplete inside a
 * Base UI Dialog. The caller supplies static commands and an exact-input
 * resolver; this component owns only behavior and chrome. No fuzzy data
 * search is implied or provided.
 */

export interface PaletteCommand {
  id: string;
  label: string;
  hint?: string;
  keywords?: string;
  disabled?: boolean;
  disabledReason?: string;
}

export function CommandDialog({
  open,
  onOpenChange,
  commands,
  resolveExact,
  onSelect,
  placeholder,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commands: readonly PaletteCommand[];
  /** Returns a command for an exact identifier input, or null. */
  resolveExact: (input: string) => PaletteCommand | null;
  onSelect: (command: PaletteCommand) => void;
  placeholder: string;
}) {
  const [query, setQuery] = useState("");

  const items = useMemo<PaletteCommand[]>(() => {
    const q = query.trim().toLowerCase();
    const exact = resolveExact(query);
    if (exact) return [exact];
    if (q === "") return [...commands];
    return commands.filter(
      (c) => c.label.toLowerCase().includes(q) || (c.keywords ?? "").toLowerCase().includes(q),
    );
  }, [commands, query, resolveExact]);

  const handleOpenChange = (next: boolean) => {
    if (!next) setQuery("");
    onOpenChange(next);
  };

  return (
    <BaseDialog.Root open={open} onOpenChange={handleOpenChange}>
      <BaseDialog.Portal>
        <BaseDialog.Backdrop className="fixed inset-0 z-(--sys-z-overlay) bg-canvas/60" />
        <BaseDialog.Popup
          className={
            "fixed top-[12vh] left-1/2 z-(--sys-z-modal) w-full max-w-xl -translate-x-1/2 " +
            "rounded-(--radius-structural) border border-border-strong bg-layer-overlay " +
            "shadow-overlay outline-none"
          }
          aria-label="Command palette"
        >
          <Autocomplete.Root
            items={items}
            value={query}
            onValueChange={setQuery}
            mode="none"
            autoHighlight="always"
            inline
            open
            onOpenChange={(nextOpen) => {
              // The inline list never closes on its own; an Escape that would
              // close the popup closes the whole palette instead.
              if (!nextOpen) handleOpenChange(false);
            }}
          >
            <label htmlFor="palette-input" className="sr-only">
              Go to view or paste an exact identifier
            </label>
            <Autocomplete.Input
              id="palette-input"
              placeholder={placeholder}
              // Base UI's inline mode omits aria-expanded, which ARIA requires
              // on role=combobox; the inline list is permanently visible.
              aria-expanded="true"
              className={
                "h-11 w-full border-b border-border-subtle bg-transparent px-4 " +
                "font-mono text-sm text-text-primary outline-none " +
                "placeholder:font-sans placeholder:text-text-tertiary"
              }
            />
            <Autocomplete.List className="max-h-80 overflow-y-auto p-1">
              {(command: PaletteCommand) => (
                <Autocomplete.Item
                  key={command.id}
                  value={command}
                  onClick={() => {
                    if (!command.disabled) onSelect(command);
                  }}
                  aria-disabled={command.disabled ? true : undefined}
                  className={
                    "flex min-h-9 items-center justify-between gap-3 rounded-(--radius-control) " +
                    "px-3 py-1.5 text-sm data-highlighted:bg-selection " +
                    (command.disabled ? "text-text-disabled" : "text-text-primary")
                  }
                >
                  <span className="truncate">{command.label}</span>
                  {command.disabled && command.disabledReason ? (
                    <span className="shrink-0 text-xs text-text-tertiary">
                      {command.disabledReason}
                    </span>
                  ) : command.hint ? (
                    <kbd className="shrink-0 font-mono text-xs text-text-tertiary">
                      {command.hint}
                    </kbd>
                  ) : null}
                </Autocomplete.Item>
              )}
            </Autocomplete.List>
            <Autocomplete.Empty className="px-4 py-6 text-center text-sm text-text-secondary">
              No matching destination. Exact 64-hex effect ids and typed ids (fnd_, run_, rcpt_)
              route directly.
            </Autocomplete.Empty>
          </Autocomplete.Root>
        </BaseDialog.Popup>
      </BaseDialog.Portal>
    </BaseDialog.Root>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd
      className={
        "inline-flex h-5 min-w-5 items-center justify-center rounded-(--radius-control) " +
        "border border-border bg-layer-sunken px-1 font-mono text-2xs text-text-secondary"
      }
    >
      {children}
    </kbd>
  );
}
