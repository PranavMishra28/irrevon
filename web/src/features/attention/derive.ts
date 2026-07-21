import type { ReconciliationFinding } from "@/shared/contracts/generated/reconciliation-finding";
import type { EffectListItem } from "@/shared/api/types";

/**
 * The exact Attention derivation (REDESIGN-BRIEF A5), shown verbatim in-UI:
 *
 *   ATTENTION =
 *     effects WHERE lifecycle = AMBIGUOUS
 *     UNION
 *     findings WHERE resolution.status IN (OPEN, ESCALATED_HUMAN)
 *
 * Work-item keys: `effect:<effect_id>` for effect-backed items,
 * `destination:<adapter_id>:<destination_ref>` for destination-keyed
 * orphans. Duplicate keys merge reasons — never scored, never ranked.
 * Groups follow the formula's fixed order; items retain source order.
 */

export const ATTENTION_FORMULA = `ATTENTION =
  effects WHERE lifecycle = AMBIGUOUS
  UNION
  findings WHERE resolution.status IN (OPEN, ESCALATED_HUMAN)`;

export type AttentionReason =
  | { kind: "ambiguous-lifecycle"; detail: string }
  | { kind: "finding-resolution"; detail: string; findingId: string };

export interface AttentionItem {
  key: string;
  /** Where the item links: an effect investigation or the findings inspector. */
  target: { kind: "effect"; effectId: string } | { kind: "finding"; findingId: string };
  /** Group index in formula order: 0 = ambiguous effects, 1 = open findings. */
  group: 0 | 1;
  title: string;
  subtitle: string;
  reasons: AttentionReason[];
}

export interface AttentionResult {
  items: AttentionItem[];
  /** true when either source envelope was partial (has_more). */
  partial: boolean;
  ambiguousCount: number;
  openFindingCount: number;
}

const OPEN_STATUSES: readonly string[] = ["OPEN", "ESCALATED_HUMAN"];

export function deriveAttention({
  effects,
  findings,
  effectsPartial,
  findingsPartial,
}: {
  effects: EffectListItem[];
  findings: ReconciliationFinding[];
  effectsPartial: boolean;
  findingsPartial: boolean;
}): AttentionResult {
  const byKey = new Map<string, AttentionItem>();
  let ambiguousCount = 0;
  let openFindingCount = 0;

  for (const item of effects) {
    if (item.record.lifecycle !== "AMBIGUOUS") continue;
    ambiguousCount += 1;
    const key = `effect:${item.record.effect_id}`;
    byKey.set(key, {
      key,
      target: { kind: "effect", effectId: item.record.effect_id },
      group: 0,
      title: item.record.effect_type,
      subtitle: item.record.scope,
      reasons: [{ kind: "ambiguous-lifecycle", detail: "lifecycle = AMBIGUOUS" }],
    });
  }

  for (const finding of findings) {
    const status = String(finding.resolution.status);
    if (!OPEN_STATUSES.includes(status)) continue;
    openFindingCount += 1;
    const reason: AttentionReason = {
      kind: "finding-resolution",
      detail: `finding ${finding.classification} · resolution.status = ${status}`,
      findingId: finding.finding_id,
    };
    if ("effect_id" in finding.subject) {
      const key = `effect:${finding.subject.effect_id}`;
      const existing = byKey.get(key);
      if (existing) {
        existing.reasons.push(reason);
        continue;
      }
      byKey.set(key, {
        key,
        target: { kind: "effect", effectId: finding.subject.effect_id },
        group: 1,
        title: `finding ${finding.classification}`,
        subtitle: finding.subject.effect_id,
        reasons: [reason],
      });
    } else {
      const key = `destination:${finding.subject.adapter_id}:${finding.subject.destination_ref}`;
      const existing = byKey.get(key);
      if (existing) {
        existing.reasons.push(reason);
        continue;
      }
      byKey.set(key, {
        key,
        target: { kind: "finding", findingId: finding.finding_id },
        group: 1,
        title: `finding ${finding.classification}`,
        subtitle: `${finding.subject.adapter_id} · ${finding.subject.destination_ref}`,
        reasons: [reason],
      });
    }
  }

  // Fixed group order (formula order), stable source order within groups —
  // Map preserves insertion order, so a sort by group alone suffices.
  const items = [...byKey.values()].sort((a, b) => a.group - b.group);

  return {
    items,
    partial: effectsPartial || findingsPartial,
    ambiguousCount,
    openFindingCount,
  };
}
