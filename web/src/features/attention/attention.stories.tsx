import type { Meta, StoryObj } from "@storybook/react-vite";
import { SunkenWell } from "@/shared/ui/primitives/panel";
import { ATTENTION_FORMULA, deriveAttention } from "./derive";
import effectsFixture from "../../../fixtures/canonical/effects.json";
import findingsFixture from "../../../fixtures/canonical/findings.json";
import type { EffectRecord } from "@/shared/contracts/generated/effect-record";
import type { EffectListItem, FindingsEnvelope } from "@/shared/api/types";

/** Derivation over the canonical fixtures — the exact production math. */
const records = (effectsFixture as { data: unknown }).data as EffectRecord[];
const findings = (findingsFixture as unknown as FindingsEnvelope).data;
const effects: EffectListItem[] = records.map((record) => {
  const finding =
    findings.find(
      (f) => "effect_id" in f.subject && f.subject.effect_id === record.effect_id,
    ) ?? null;
  return {
    record,
    classification: finding ? finding.classification : "UNRECONCILED",
    finding,
  };
});
const result = deriveAttention({
  effects,
  findings,
  effectsPartial: false,
  findingsPartial: false,
});

const meta = {
  title: "Attention/Derivation",
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const FormulaVerbatim: Story = {
  render: () => (
    <div className="max-w-md">
      <SunkenWell scrollX>
        <pre className="font-mono text-xs leading-relaxed text-text-primary">
          {ATTENTION_FORMULA}
        </pre>
      </SunkenWell>
    </div>
  ),
};

export const DerivedWorkItems: Story = {
  render: () => (
    <ul className="flex max-w-lg flex-col gap-2">
      {result.items.map((item) => (
        <li
          key={item.key}
          className={
            "flex flex-col gap-1 rounded-(--radius-structural) border border-border-subtle " +
            "bg-layer-panel p-(--dt-panel-pad) shadow-(--sys-edge-light)"
          }
        >
          <span className="machine-id font-mono text-xs font-medium text-text-primary">
            {item.title}
          </span>
          <span className="machine-id font-mono text-2xs text-text-tertiary">{item.key}</span>
          {item.reasons.map((reason) => (
            <span key={reason.detail} className="font-mono text-2xs text-text-tertiary">
              included because: {reason.detail}
            </span>
          ))}
        </li>
      ))}
    </ul>
  ),
};
