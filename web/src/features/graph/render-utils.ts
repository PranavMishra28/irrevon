import type { GraphEdge, GraphModel } from "./model";

/** Display truncation per the identifier contract (§3.4). */
export function truncateGraphValue(value: string): string {
  if (/^[0-9a-f]{64}$/.test(value)) return `${value.slice(0, 12)}…`;
  if (/^[0-9a-f]{64}:\d+$/.test(value)) {
    const colon = value.indexOf(":");
    return `${value.slice(0, 12)}…${value.slice(colon)}`;
  }
  if (/^(sha256:)?[0-9a-f]{40,}$/.test(value)) {
    const prefix = value.startsWith("sha256:") ? "sha256:" : "";
    const hex = value.slice(prefix.length);
    return `${prefix}${hex.slice(0, 8)}…${hex.slice(-4)}`;
  }
  return value;
}

/**
 * The ancestor path back to the intent node: selected node + every edge/node
 * reachable by walking edges in reverse. Deterministic class toggles only.
 */
export function ancestorPath(
  model: GraphModel,
  selectedId: string,
): { nodes: Set<string>; edges: Set<string> } {
  const nodes = new Set<string>([selectedId]);
  const edges = new Set<string>();
  const queue = [selectedId];
  const incoming = new Map<string, GraphEdge[]>();
  for (const edge of model.edges) {
    const list = incoming.get(edge.to) ?? [];
    list.push(edge);
    incoming.set(edge.to, list);
  }
  while (queue.length > 0) {
    const current = queue.shift();
    if (current === undefined) break;
    for (const edge of incoming.get(current) ?? []) {
      if (!edges.has(edge.id)) {
        edges.add(edge.id);
        if (!nodes.has(edge.from)) {
          nodes.add(edge.from);
          queue.push(edge.from);
        }
      }
    }
  }
  return { nodes, edges };
}
