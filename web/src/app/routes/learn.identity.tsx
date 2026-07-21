import { createFileRoute } from "@tanstack/react-router";
import { EXAMPLE_ORDER_CREATE } from "@/shared/contracts/generated/identity-examples";
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
            Worked example — from the ratified request schema
          </h2>
          <p className="mt-2 text-sm text-text-secondary">
            This is the canonical <span className="font-mono text-xs">order.create</span>{" "}
            example from the schema's own acceptance suite. Only the highlighted identity fields
            participate in the hash; everything else is a carrier.
          </p>
          <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
            {Object.entries(EXAMPLE_ORDER_CREATE).map(([field, value]) => {
              const isIdentity =
                field === "stable_ids" || field === "effect_type" || field === "scope";
              return (
                <div key={field} className="col-span-2 grid grid-cols-subgrid">
                  <dt
                    className={
                      "font-mono text-xs " +
                      (isIdentity ? "font-semibold text-text-primary" : "text-text-tertiary")
                    }
                  >
                    {field}
                    {isIdentity ? (
                      <span className="ml-1.5 rounded-(--radius-structural) border border-border-strong px-1 font-mono text-2xs text-text-secondary uppercase">
                        identity
                      </span>
                    ) : null}
                  </dt>
                  <dd
                    className={
                      "font-mono text-xs break-all " +
                      (isIdentity ? "text-text-primary" : "text-text-tertiary")
                    }
                  >
                    {typeof value === "string" ? value : JSON.stringify(value)}
                  </dd>
                </div>
              );
            })}
          </dl>
          <p className="mt-4 border-t border-border-subtle pt-3 text-sm text-text-secondary">
            intent_id = SHA-256 over the canonical (JCS) bytes of{" "}
            <span className="font-mono text-xs">{"{stable_ids, effect_type, scope}"}</span>. A
            retry that re-synthesizes different{" "}
            <span className="font-mono text-xs">parameters</span> — new line-item order, new
            prose, new anything — produces the same intent_id, and the deduplication gate
            answers it with evidence instead of a second effect.
          </p>
        </div>
      </div>
    </Page>
  );
}
