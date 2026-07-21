import type { GraphModel } from "./model";
import { truncateGraphValue } from "./render-utils";

/**
 * The semantic Connections table — the accessible twin of the aria-hidden
 * SVG connector layer (REDESIGN-BRIEF A8). Every edge appears here with its
 * exact relation and the contract field that justifies it. No fact exists
 * only in a drawn line.
 */
export function ConnectionsTable({ model }: { model: GraphModel }) {
  const names = new Map(
    model.nodes.map((n) => [n.id, `${n.kindLabel} ${truncateGraphValue(n.primary)}`]),
  );
  return (
    <section aria-label="Connections" className="min-w-0">
      <h3 className="border-b border-border-subtle pb-1.5 font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase">
        Connections — semantic twin of the drawn edges ({model.edges.length})
      </h3>
      <div
        role="group"
        aria-label="Connections table, scroll horizontally if needed"
        tabIndex={-1}
        className="overflow-x-auto"
      >
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              {["From", "Relation", "To", "Evidence path"].map((column) => (
                <th
                  key={column}
                  scope="col"
                  className="border-b border-border-subtle px-2 py-1.5 text-left font-mono text-2xs font-medium tracking-wide text-text-tertiary uppercase"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {model.edges.map((edge) => (
              <tr key={edge.id} className="border-b border-border-subtle last:border-b-0">
                <td className="machine-id px-2 py-1 font-mono text-2xs text-text-primary">
                  {names.get(edge.from) ?? edge.from}
                </td>
                <td className="px-2 py-1 font-mono text-2xs text-text-secondary">
                  {edge.relation}
                  {edge.stroke !== "solid" ? ` (${edge.stroke})` : ""}
                </td>
                <td className="machine-id px-2 py-1 font-mono text-2xs text-text-primary">
                  {names.get(edge.to) ?? edge.to}
                </td>
                <td className="machine-id px-2 py-1 font-mono text-2xs break-all text-text-tertiary">
                  {edge.evidencePath}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
