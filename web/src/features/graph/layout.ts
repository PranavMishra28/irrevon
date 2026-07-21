import type { GraphAnnotation, GraphEdge, GraphModel, GraphNode } from "./model";

/**
 * Deterministic fixed-rank layout (REDESIGN-BRIEF §4.3). Rank = node kind;
 * within-rank order comes from the model's (created_at, stable id) key.
 * Fixed node boxes, integer coordinates, no text measurement, no floats ⇒
 * byte-stable output for byte-stable fixtures. Left-to-right at ≥1024,
 * top-to-bottom below. Lateral nodes (denies, variants, probes, flanks)
 * occupy a fixed secondary lane.
 */

export type Orientation = "horizontal" | "vertical";

export interface PositionedNode extends GraphNode {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PositionedEdge extends GraphEdge {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  labelX: number;
  labelY: number;
}

export interface PositionedAnnotation extends GraphAnnotation {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface GraphLayout {
  orientation: Orientation;
  nodes: PositionedNode[];
  edges: PositionedEdge[];
  annotations: PositionedAnnotation[];
  width: number;
  height: number;
}

const SIZES = {
  standard: { w: 176, h: 88 },
  gate: { w: 88, h: 88 },
  compact: { w: 112, h: 56 },
} as const;

const MARGIN = 16;
const RANK_GAP = 48;
const ROW_GAP = 20;
const LANE_GAP = 44;

const V_WIDTH = 328;
const V_CARD_W = 296;
const V_GAP = 28;

function box(node: GraphNode): { w: number; h: number } {
  return SIZES[node.size];
}

export function layoutGraph(model: GraphModel, orientation: Orientation): GraphLayout {
  return orientation === "horizontal" ? layoutHorizontal(model) : layoutVertical(model);
}

function layoutHorizontal(model: GraphModel): GraphLayout {
  // Compress to non-empty ranks, keeping annotation boundaries resolvable.
  const usedRanks = [...new Set(model.nodes.map((n) => n.rank))].sort((a, b) => a - b);

  // Column geometry.
  const colWidth = new Map<number, number>();
  for (const rank of usedRanks) {
    const widths = model.nodes.filter((n) => n.rank === rank).map((n) => box(n).w);
    colWidth.set(rank, Math.max(...widths));
  }
  const colX = new Map<number, number>();
  let x = MARGIN;
  for (const rank of usedRanks) {
    colX.set(rank, x);
    x += (colWidth.get(rank) ?? 0) + RANK_GAP;
  }
  const width = x - RANK_GAP + MARGIN;

  // Main lane: stack per rank; lane height = tallest main stack.
  const mainHeights = new Map<number, number>();
  for (const rank of usedRanks) {
    let h = 0;
    for (const node of model.nodes.filter((n) => n.rank === rank && !n.lateral)) {
      h += box(node).h + ROW_GAP;
    }
    mainHeights.set(rank, h === 0 ? 0 : h - ROW_GAP);
  }
  const mainLaneHeight = Math.max(0, ...mainHeights.values());
  const lateralY = MARGIN + mainLaneHeight + LANE_GAP;

  const nodes: PositionedNode[] = [];
  for (const rank of usedRanks) {
    let mainY = MARGIN;
    let latY = lateralY;
    for (const node of model.nodes.filter((n) => n.rank === rank)) {
      const { w, h } = box(node);
      const cx = (colX.get(rank) ?? MARGIN) + ((colWidth.get(rank) ?? w) - w) / 2;
      if (node.lateral) {
        nodes.push({ ...node, x: cx, y: latY, w, h });
        latY += h + ROW_GAP;
      } else {
        nodes.push({ ...node, x: cx, y: mainY, w, h });
        mainY += h + ROW_GAP;
      }
    }
  }
  const height = Math.max(...nodes.map((n) => n.y + n.h)) + MARGIN;

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const edges: PositionedEdge[] = model.edges.flatMap((edge) => {
    const from = byId.get(edge.from);
    const to = byId.get(edge.to);
    if (!from || !to) return [];
    let x1: number, y1: number, x2: number, y2: number;
    if (to.x > from.x + from.w) {
      // forward
      x1 = from.x + from.w;
      y1 = from.y + from.h / 2;
      x2 = to.x;
      y2 = to.y + to.h / 2;
    } else if (from.x > to.x + to.w) {
      // backward (cites)
      x1 = from.x;
      y1 = from.y + from.h / 2;
      x2 = to.x + to.w;
      y2 = to.y + to.h / 2;
    } else if (to.y > from.y) {
      // same column, downward
      x1 = from.x + from.w / 2;
      y1 = from.y + from.h;
      x2 = to.x + to.w / 2;
      y2 = to.y;
    } else {
      x1 = from.x + from.w / 2;
      y1 = from.y;
      x2 = to.x + to.w / 2;
      y2 = to.y + to.h;
    }
    return [
      {
        ...edge,
        x1,
        y1,
        x2,
        y2,
        labelX: Math.round((x1 + x2) / 2),
        labelY: Math.round((y1 + y2) / 2) - 6,
      },
    ];
  });

  const annotations: PositionedAnnotation[] = model.annotations.flatMap((annotation) => {
    // The boundary before this rank: midway through the preceding gap.
    const nextRank = usedRanks.find((rank) => rank >= annotation.beforeRank);
    if (nextRank === undefined) return [];
    const boundaryX = (colX.get(nextRank) ?? MARGIN) - RANK_GAP / 2;
    return [
      {
        ...annotation,
        x1: boundaryX,
        y1: MARGIN,
        x2: boundaryX,
        y2: Math.max(MARGIN + mainLaneHeight, MARGIN + 88),
      },
    ];
  });

  return { orientation: "horizontal", nodes, edges, annotations, width, height };
}

function layoutVertical(model: GraphModel): GraphLayout {
  // One centered column: ranks become bands top-to-bottom; each rank lists
  // its main nodes then its laterals. Cards take min(296px, available).
  const usedRanks = [...new Set(model.nodes.map((n) => n.rank))].sort((a, b) => a - b);
  const nodes: PositionedNode[] = [];
  const annotations: PositionedAnnotation[] = [];
  let y = MARGIN;

  for (const rank of usedRanks) {
    for (const annotation of model.annotations) {
      const boundaryRank = usedRanks.find((r) => r >= annotation.beforeRank);
      if (boundaryRank === rank) {
        annotations.push({
          ...annotation,
          x1: MARGIN,
          y1: y,
          x2: V_WIDTH - MARGIN,
          y2: y,
        });
        y += V_GAP;
      }
    }
    for (const node of model.nodes.filter((n) => n.rank === rank)) {
      const h = node.size === "compact" ? 56 : 88;
      const w = node.size === "gate" ? 128 : V_CARD_W;
      nodes.push({ ...node, x: (V_WIDTH - w) / 2, y, w, h });
      y += h + V_GAP;
    }
  }
  const height = y - V_GAP + MARGIN;

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const edges: PositionedEdge[] = model.edges.flatMap((edge) => {
    const from = byId.get(edge.from);
    const to = byId.get(edge.to);
    if (!from || !to) return [];
    if (to.y > from.y) {
      const isAdjacent = to.y - (from.y + from.h) <= V_GAP;
      if (isAdjacent) {
        return [
          {
            ...edge,
            x1: from.x + from.w / 2,
            y1: from.y + from.h,
            x2: to.x + to.w / 2,
            y2: to.y,
            labelX: from.x + from.w / 2 + 8,
            labelY: Math.round((from.y + from.h + to.y) / 2),
          },
        ];
      }
      // Long forward hop: run along the right margin.
      return [
        {
          ...edge,
          x1: from.x + from.w,
          y1: from.y + from.h / 2,
          x2: to.x + to.w,
          y2: to.y + to.h / 2,
          labelX: V_WIDTH - MARGIN - 4,
          labelY: Math.round((from.y + to.y) / 2),
        },
      ];
    }
    // Backward (cites): run along the left margin.
    return [
      {
        ...edge,
        x1: from.x,
        y1: from.y + from.h / 2,
        x2: to.x,
        y2: to.y + to.h / 2,
        labelX: MARGIN + 4,
        labelY: Math.round((from.y + to.y) / 2),
      },
    ];
  });

  return { orientation: "vertical", nodes, edges, annotations, width: V_WIDTH, height };
}
