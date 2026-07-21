import { useNavigate } from "@tanstack/react-router";
import { useCallback } from "react";
import { parseExactId, truncateEffectId, truncateTypedId } from "@/shared/lib/ids";
import { CommandDialog, type PaletteCommand } from "@/shared/ui/primitives/command-dialog";

/**
 * v0.1 palette: static route navigation plus exact-ID routing.
 * - exact 64-hex → effect detail
 * - fnd_/run_ → the shipped placeholder surface that owns that id kind
 * - rcpt_ → no navigable destination in v0.1 (disabled entry, honest reason)
 * No prefix lookup and no fuzzy ledger search.
 */

const STATIC_COMMANDS: readonly PaletteCommand[] = [
  { id: "/effects", label: "Effects", hint: "g e", keywords: "ledger list records" },
  { id: "/demo", label: "Demo", hint: "g d", keywords: "playback walkthrough flagship" },
  { id: "/learn/start", label: "Learn: Start Here", keywords: "onboarding intro" },
  { id: "/learn/identity", label: "Learn: Identity", keywords: "hash stable ids intent" },
  { id: "/learn/state", label: "Learn: State model", keywords: "lifecycle transitions" },
  { id: "/learn/tiers", label: "Learn: Capability tiers", keywords: "c1 c2 c3 guarantees" },
  { id: "/attention", label: "Attention", keywords: "ambiguous open work" },
  { id: "/findings", label: "Findings", keywords: "reconciliation classification" },
  { id: "/adapters", label: "Adapters", keywords: "destinations declarations" },
  { id: "/bench", label: "Benchmark", hint: "g b", keywords: "detentbench runs" },
  { id: "/health", label: "Health", hint: "g h", keywords: "doctor connection checks" },
];

export function Palette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const navigate = useNavigate();

  const resolveExact = useCallback((input: string): PaletteCommand | null => {
    const parsed = parseExactId(input);
    switch (parsed.kind) {
      case "effect":
        return {
          id: `/effects/${parsed.effectId}`,
          label: `Open effect ${truncateEffectId(parsed.effectId)}`,
          hint: "exact id",
        };
      case "operation":
        return {
          id: `/effects/${parsed.effectId}`,
          label: `Open effect ${truncateEffectId(parsed.effectId)} (operation step ${String(parsed.step)})`,
          hint: "exact id",
        };
      case "finding":
        return {
          id: "/findings",
          label: `Findings surface for ${truncateTypedId(parsed.id)}`,
          hint: "placeholder",
        };
      case "run":
        return {
          id: "/bench",
          label: `Benchmark surface for ${truncateTypedId(parsed.id)}`,
          hint: "placeholder",
        };
      case "receipt":
        return {
          id: "noop-receipt",
          label: `Receipt ${truncateTypedId(parsed.id)}`,
          disabled: true,
          disabledReason: "no receipt route in v0.1",
        };
      case "none":
        return null;
    }
  }, []);

  const handleSelect = useCallback(
    (command: PaletteCommand) => {
      if (command.disabled || !command.id.startsWith("/")) return;
      onOpenChange(false);
      void navigate({ to: command.id });
    },
    [navigate, onOpenChange],
  );

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      commands={STATIC_COMMANDS}
      resolveExact={resolveExact}
      onSelect={handleSelect}
      placeholder="Go to view, or paste an exact effect / finding / run id"
    />
  );
}
