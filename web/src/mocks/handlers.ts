import { HttpResponse, http } from "msw";
import adaptersFixture from "../../fixtures/canonical/adapters.json";
import demoArtifactFixture from "../../fixtures/canonical/demo-artifact.json";
import effectsFixture from "../../fixtures/canonical/effects.json";
import findingsFixture from "../../fixtures/canonical/findings.json";
import healthFixture from "../../fixtures/canonical/health.json";
import inspectAmbiguous from "../../fixtures/canonical/inspect/f18adfccc0bfa6fabc817c15e2afd305a80c5d119f1c7101567cf43f28a913b0.json";
import inspectClean from "../../fixtures/canonical/inspect/c4ea734f26decc15b551c4d91fb7a27dcaa4f1005cc9b4d1d17adf0bd0cb5ed7.json";
import inspectDuplicate from "../../fixtures/canonical/inspect/efcd86f31233098669466ff0afef22407bb52cb9f557d352685c8e7e785b7954.json";
import inspectFlagship from "../../fixtures/canonical/inspect/0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5.json";
import inspectLost from "../../fixtures/canonical/inspect/c85c01dc4fe6fd581e7b528ac1baacc59490e5d195f3a16c427e3ee516214817.json";
import inspectPersisted from "../../fixtures/canonical/inspect/371a59b8452dd4fe659e9dd4ef78fd8cac90b5dd36583aea1dff9e99b4f74f6c.json";
import inspectRejected from "../../fixtures/canonical/inspect/e216ca270fe757cdc2c2f435a06c8f42855056a8220cb63c2ea789caaaf70b20.json";
import type { EffectRecord } from "@/shared/contracts/generated/effect-record";
import type { ReconciliationFinding } from "@/shared/contracts/generated/reconciliation-finding";
import type { EffectListItem, EffectsEnvelope } from "@/shared/api/types";

/**
 * MSW is the only mock transport. Every payload is a captured transcript of
 * the real engine (fixtures/canonical/provenance.json). Handlers only filter
 * and page — they never synthesize values.
 */

const records = effectsFixture.data as unknown as EffectRecord[];
const findings = findingsFixture.data as unknown as ReconciliationFinding[];

const inspectPayloads: Record<string, unknown> = Object.fromEntries(
  [
    inspectFlagship,
    inspectClean,
    inspectRejected,
    inspectLost,
    inspectDuplicate,
    inspectPersisted,
    inspectAmbiguous,
  ].map((payload) => [
    (payload as { record: { effect_id: string } }).record.effect_id,
    payload,
  ]),
);

function itemFor(record: EffectRecord): EffectListItem {
  const finding =
    findings.find(
      (f) => "effect_id" in f.subject && f.subject.effect_id === record.effect_id,
    ) ?? null;
  return {
    record,
    classification: finding ? finding.classification : "UNRECONCILED",
    finding,
  };
}

const PAGE_SIZE = 50;

export const handlers = [
  http.get("/api/v1/effects", ({ request }) => {
    const url = new URL(request.url);
    const lifecycle = url.searchParams.getAll("lifecycle");
    const classification = url.searchParams.getAll("classification");
    const effectType = url.searchParams.get("effect_type");
    const cursor = url.searchParams.get("cursor");

    let items = records.map(itemFor);
    if (lifecycle.length > 0) {
      items = items.filter((i) => lifecycle.includes(i.record.lifecycle));
    }
    if (classification.length > 0) {
      items = items.filter((i) => classification.includes(i.classification));
    }
    if (effectType !== null && effectType !== "") {
      items = items.filter((i) => i.record.effect_type === effectType);
    }

    const start = cursor === null ? 0 : Number.parseInt(cursor, 10) || 0;
    const page = items.slice(start, start + PAGE_SIZE);
    const hasMore = start + PAGE_SIZE < items.length;
    const envelope: EffectsEnvelope = {
      schema_version: "1",
      data: page,
      has_more: hasMore,
      next_cursor: hasMore ? String(start + PAGE_SIZE) : null,
      as_of: effectsFixture.as_of,
    };
    return HttpResponse.json(envelope);
  }),

  http.get("/api/v1/effects/:effectId/inspect", ({ params }) => {
    const payload = inspectPayloads[String(params.effectId)];
    if (!payload) return HttpResponse.json({ error: "not_found" }, { status: 404 });
    return HttpResponse.json(payload);
  }),

  http.get("/api/v1/effects/:effectId", ({ params }) => {
    const record = records.find((r) => r.effect_id === params.effectId);
    if (!record) return HttpResponse.json({ error: "not_found" }, { status: 404 });
    return HttpResponse.json({ schema_version: "1", ...itemFor(record) });
  }),

  http.get("/api/v1/findings", () => HttpResponse.json(findingsFixture)),
  http.get("/api/v1/adapters", () => HttpResponse.json(adaptersFixture)),
  http.get("/api/v1/health", () => HttpResponse.json(healthFixture)),
  http.get("/api/v1/demo/artifact", () => HttpResponse.json(demoArtifactFixture)),
];
