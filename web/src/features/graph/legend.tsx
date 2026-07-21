/**
 * The always-visible legend (graph-semantics §1.3, verbatim vocabulary).
 * It is itself the text key: every active visual channel is described in
 * words — no fact exists only in a stroke, pattern, or color.
 */

const CHANNELS: readonly {
  swatch: "solid" | "dashed" | "interrupted" | "hatched" | "void" | "notch" | "selected";
  label: string;
}[] = [
  { swatch: "solid", label: "solid = a recorded ledger row (or its exchange-shape view)" },
  { swatch: "dashed", label: "dashed = declared or intended — asserted, not observed" },
  {
    swatch: "interrupted",
    label: "interrupted ⌁ = evidence gap: bytes left, no recognized answer",
  },
  {
    swatch: "hatched",
    label: "hatched = destination-side observation — probe/receipt-mediated, not ledger truth",
  },
  { swatch: "void", label: "dashed void frame = explicit absence, always labeled" },
  {
    swatch: "notch",
    label: "notch ⟟ = the irreversible dispatch boundary — reconcile or compensate only",
  },
  {
    swatch: "selected",
    label: "accent frame + ticks = the one selected node; its ancestor path is emphasized",
  },
];

function Swatch({ kind }: { kind: (typeof CHANNELS)[number]["swatch"] }) {
  const common = "inline-block h-4 w-7 shrink-0 rounded-(--radius-structural)";
  switch (kind) {
    case "solid":
      return <span aria-hidden className={`${common} border border-border bg-layer-panel`} />;
    case "dashed":
      return <span aria-hidden className={`${common} border border-dashed border-border`} />;
    case "interrupted":
      return (
        <svg aria-hidden viewBox="0 0 28 16" className="h-4 w-7 shrink-0">
          <line
            x1="1"
            y1="8"
            x2="27"
            y2="8"
            strokeWidth="1.5"
            strokeDasharray="2 6"
            className="stroke-(--color-border-strong)"
          />
        </svg>
      );
    case "hatched":
      return <span aria-hidden className={`${common} dt-hatched border border-border`} />;
    case "void":
      return <span aria-hidden className={`${common} border border-dashed border-border`} />;
    case "notch":
      return (
        <svg aria-hidden viewBox="0 0 28 16" className="h-4 w-7 shrink-0">
          <line
            x1="14"
            y1="1"
            x2="14"
            y2="15"
            strokeWidth="2"
            className="stroke-(--color-border-strong)"
          />
          <path d="M9,1 h10 l-5,7 z" className="fill-(--color-border-strong)" />
        </svg>
      );
    case "selected":
      return (
        <span
          aria-hidden
          className={`${common} border border-(--color-accent)`}
          style={{ outline: "1px solid var(--color-accent)", outlineOffset: "1px" }}
        />
      );
  }
}

export function GraphLegend() {
  return (
    <section
      aria-label="Graph legend"
      className={
        "rounded-(--radius-structural) border border-border-subtle bg-layer-panel " +
        "p-(--dt-panel-pad) shadow-(--sys-edge-light)"
      }
    >
      <h3 className="font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
        Legend — every channel, in words
      </h3>
      <ul className="mt-2 flex flex-col gap-1.5">
        {CHANNELS.map((channel) => (
          <li key={channel.label} className="flex items-center gap-2">
            <Swatch kind={channel.swatch} />
            <span className="text-2xs text-text-secondary">{channel.label}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
