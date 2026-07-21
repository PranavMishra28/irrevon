import type { CapabilityDeclaration } from "@/shared/contracts/generated/capability-declaration";
import { SunkenWell } from "@/shared/ui/primitives/panel";

/**
 * Declared adapter topology (REDESIGN-BRIEF §5.7, graph-semantics §1.4c):
 * Caller → Detent → adapter(s) → destination(s). Caller and Detent carry a
 * persistent CONCEPTUAL label (no contract row backs them); adapter and
 * destination nodes are factual/declarative, and the adapter→destination
 * edge is dashed — DECLARED, not observed. The declaration cards below are
 * the complete accessible twin.
 */
export function AdapterTopology({
  declarations,
  vertical = false,
}: {
  declarations: CapabilityDeclaration[];
  vertical?: boolean;
}) {
  const conceptualNode =
    "flex flex-col gap-0.5 rounded-(--radius-structural) border border-dashed border-border " +
    "px-2.5 py-1.5";
  const factualNode =
    "flex flex-col gap-0.5 rounded-(--radius-structural) border border-border " +
    "bg-layer-panel px-2.5 py-1.5 shadow-(--sys-edge-light)";

  const arrow = (label: string, dashed: boolean) => (
    <span
      className={
        "flex items-center gap-1 font-mono text-2xs text-text-tertiary " +
        (vertical ? "flex-col py-0.5" : "px-0.5")
      }
    >
      <span aria-hidden className={vertical ? "" : ""}>
        {vertical ? "↓" : "→"}
      </span>
      <span className={dashed ? "italic" : ""}>{label}</span>
    </span>
  );

  return (
    <figure className="min-w-0">
      <SunkenWell scrollX scrollLabel="Adapter topology, scroll horizontally if needed">
        <div
          className={
            "flex gap-1 py-1 " +
            (vertical ? "flex-col items-stretch" : "flex-row flex-wrap items-center gap-y-2")
          }
        >
          <div className={conceptualNode}>
            <span className="font-mono text-[10px] font-medium tracking-wide text-text-tertiary uppercase">
              Caller — CONCEPTUAL
            </span>
            <span className="text-xs text-text-secondary">any agent or workflow runtime</span>
          </div>
          {arrow("registers intent", false)}
          <div className={conceptualNode}>
            <span className="font-mono text-[10px] font-medium tracking-wide text-text-tertiary uppercase">
              Detent — CONCEPTUAL
            </span>
            <span className="text-xs text-text-secondary">ledger · gate · reconciler</span>
          </div>
          {declarations.map((declaration) => (
            <div
              key={declaration.adapter}
              className={
                "flex gap-1 " +
                (vertical
                  ? "flex-col items-stretch"
                  : "flex-row flex-wrap items-center gap-y-2")
              }
            >
              {arrow("dispatches through", false)}
              <a href={`#declaration-${declaration.adapter}`} className={factualNode}>
                <span className="font-mono text-[10px] font-medium tracking-wide text-text-tertiary uppercase">
                  Adapter · tier {declaration.tier}
                </span>
                <span className="machine-id font-mono text-xs text-text-primary">
                  {declaration.adapter}
                </span>
              </a>
              {arrow(`declared (${declaration.evidence_quality})`, true)}
              <div className={`${factualNode} dt-hatched border-dashed`}>
                <span className="font-mono text-[10px] font-medium tracking-wide text-text-tertiary uppercase">
                  Destination — declared
                </span>
                <span className="text-xs text-text-primary">{declaration.destination}</span>
              </div>
            </div>
          ))}
        </div>
      </SunkenWell>
      <figcaption className="mt-1.5 text-2xs text-text-tertiary">
        Dashed adapter→destination means DECLARED, not observed. Caller and Detent are
        conceptual — no contract row backs them. Exact fields live in the declaration cards.
      </figcaption>
    </figure>
  );
}
