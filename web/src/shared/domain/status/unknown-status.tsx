import { HelpCircle } from "@/shared/ui/icons";

/**
 * Runtime boundary guard: an enum value the generated contracts do not know
 * renders as neutral UNKNOWN with the raw escaped value — never silently
 * coerced to the nearest known state.
 */
export function UnknownStatus({ dimension, value }: { dimension: string; value: string }) {
  return (
    <span className="inline-flex h-5 items-center gap-1 rounded-full border border-border bg-status-neutral-bg px-2 text-status-neutral">
      <span className="sr-only">
        Unknown {dimension} value: {value}
      </span>
      <span aria-hidden className="flex items-center gap-1">
        <HelpCircle size={12} />
        <span className="font-mono text-2xs font-medium tracking-wide uppercase">
          UNKNOWN({JSON.stringify(value)})
        </span>
      </span>
    </span>
  );
}
