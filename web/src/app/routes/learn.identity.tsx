import { createFileRoute } from "@tanstack/react-router";
import { Page } from "@/shared/ui/layout/page";

export const Route = createFileRoute("/learn/identity")({ component: IdentityPage });

const STAGES: readonly { name: string; body: string }[] = [
  {
    name: "Stable identifiers",
    body:
      "Identity starts from upstream business facts — order ids, invoice ids, approved task ids, " +
      "authorization ids. Never from model-generated arguments: a retried agent will re-synthesize " +
      "different arguments for the same intent, so argument hashing is structurally unsound.",
  },
  {
    name: "Canonicalization",
    body:
      "The stable identifiers, the effect type, and the scope are serialized canonically so that " +
      "the same intent always produces the same bytes — key order, encoding, and absence are all pinned.",
  },
  {
    name: "Hash → intent identity",
    body:
      "intent_id = hash(canonical stable ids + effect_type + scope). The effect record's identity " +
      "is this hash. Two registrations with the same business identity collide here, by construction.",
  },
  {
    name: "Operation identity",
    body:
      "operation_id = (intent_id, step). Idempotency evidence derives only from operation_id — " +
      "no key-derivation path reads model output. A new step is a new key; a retry of the same step is not.",
  },
];

function IdentityPage() {
  return (
    <Page
      title="Identity"
      lead="How a stable business identity is derived — and why a re-synthesized retry maps onto the same effect instead of creating a second one."
    >
      <div className="max-w-3xl">
        <ol className="flex flex-col">
          {STAGES.map((stage, index) => (
            <li key={stage.name} className="relative flex gap-4 pb-6 last:pb-0">
              {index < STAGES.length - 1 ? (
                <span
                  aria-hidden
                  className="absolute top-7 left-[13px] h-[calc(100%-1.75rem)] w-px bg-border"
                />
              ) : null}
              <span
                aria-hidden
                className={
                  "mt-0.5 flex size-7 shrink-0 items-center justify-center " +
                  "rounded-full border border-border-strong bg-surface-1 " +
                  "font-mono text-xs font-medium text-text-secondary"
                }
              >
                {index + 1}
              </span>
              <div>
                <h2 className="text-base font-semibold text-text-primary">{stage.name}</h2>
                <p className="mt-1 text-sm text-text-secondary">{stage.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-6 rounded-(--radius-structural) border border-border bg-surface-1 p-5">
          <h2 className="text-base font-semibold text-text-primary">
            Worked example — pending the corrected request schema
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            A concrete request-to-hash walkthrough belongs here, derived field-by-field from the
            ratified dispatchable-request schema. That schema is still being corrected (
            <span className="font-mono text-xs">BI-1, BI-2</span>); this page will not invent
            example payloads from stale drafts.
          </p>
        </div>
      </div>
    </Page>
  );
}
