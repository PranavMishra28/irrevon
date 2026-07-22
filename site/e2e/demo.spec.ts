// /demo gates:
//   - anti-fabrication: every rendered number/id/status must match the synced
//     recorded artifact JSON (the page is built FROM that JSON; this test
//     proves the rendered HTML never drifts from it).
//   - island budget: the demo island stays ≤8 KB source (inside the global
//     10 KB inline gate, which is unchanged).
//   - step-driven interaction: keyboard arrows/Home/End, rail, hash deep
//     links; no autoplay; backward scrubbing is instant re-inspection.
//   - no-JS completeness: all twelve beats render in document order.
import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

const artifact = JSON.parse(readFileSync(new URL("../src/data/demo/demo-artifact.json", import.meta.url), "utf8"));
const inspect = JSON.parse(readFileSync(new URL("../src/data/demo/flagship-inspect.json", import.meta.url), "utf8"));
const provenance = JSON.parse(readFileSync(new URL("../src/data/demo/provenance.json", import.meta.url), "utf8"));

const events = artifact.events;
const summary = artifact.summary;
const effectId: string = events[0].effect_id;

test("anti-fabrication: every rendered value matches the recorded artifact", async ({ page }) => {
  await page.goto("/demo/");
  const html = await page.content();

  // Values the page MUST carry, all derived from the artifact/inspect JSON.
  const required: [string, string][] = [
    ["truncated effect id", `${effectId.slice(0, 12)}…`],
    ["seed", `seed ${summary.seed}`],
    ["engine commit", `engine ${provenance.engine_commit.slice(0, 7)}`],
    ["adapter", inspect.record.adapter_id],
    ["lifecycle registered", events[0].lifecycle],
    ["fault", events[1].fault],
    ["lifecycle ambiguous", events[1].lifecycle],
    ["exit status", String(events[2].exit_status)],
    ["recovery scanned", String(events[3].recovery.scanned)],
    ["recovery adjudicated", String(events[3].recovery.adjudicated)],
    ["settled lifecycle", events[4].lifecycle],
    ["classification", events[4].classification],
    ["deny check", events[6].deny_check],
    ["deny outcome", events[6].outcome],
    ["deny decision id", `decision_id ${events[6].decision_id}`],
    ["b5 transport outcome", `transport_outcome ${events[7].transport_outcome}`],
    ["b5 retried op", events[9].retried[0]],
    ["b5 destination effects", `destination_effects ${events[10].destination_effects}`],
    ["contrast holds", String(summary.contrast_holds)],
    ["irrevon leg effects", `${summary.irrevon_leg.destination_effects} destination effect`],
    ["b5 leg effects", `${summary.b5_leg.destination_effects} destination effects`],
    ["variant digest prefix", events[5].parameter_variant.slice(0, 13)],
    ["allow decision", `decision_id ${inspect.gate_decisions[0].decision_id}`],
    ["probe result", inspect.probes[0].result],
    ["stable id keys", Object.keys(inspect.record.stable_ids).join(" · ")],
  ];
  for (const [label, value] of required) {
    expect(html, `missing recorded value (${label}): ${value}`).toContain(value);
  }

  // The full untruncated effect id must never be silently replaced by a
  // different id: any 64-hex string on the page must be the recorded one or
  // the recorded variant digest.
  const hexes = html.match(/[0-9a-f]{64}/g) ?? [];
  const allowed = new Set([effectId, events[5].parameter_variant.replace("sha256:", "")]);
  for (const h of hexes) expect(allowed.has(h), `unexpected 64-hex value ${h}`).toBe(true);
});

test("island budget: demo island ≤8 KB source; page inline JS ≤10 KB", async ({ page }) => {
  await page.goto("/demo/");
  const sizes = await page.evaluate(() =>
    Array.from(document.querySelectorAll("script"))
      .filter((s) => !s.src)
      .map((s) => s.textContent?.length ?? 0),
  );
  const island = Math.max(...sizes);
  expect(island).toBeLessThanOrEqual(8 * 1024);
  expect(sizes.reduce((a, b) => a + b, 0)).toBeLessThanOrEqual(10 * 1024);
});

test("stepper: collapses to one beat, arrows/Home/End step, rail jumps, hash deep-links", async ({ page }) => {
  await page.goto("/demo/");
  const app = page.locator("#demo-app");
  await expect(app).toHaveAttribute("data-mode", "stepper");
  await expect(page.locator(".beat.active")).toHaveCount(1);
  await expect(page.locator("#beat-01")).toBeVisible();
  await expect(page.locator("#beat-02")).toBeHidden();

  // No autoplay: the beat must not advance on its own.
  await page.waitForTimeout(600);
  await expect(page.locator("#beat-01")).toBeVisible();

  await page.locator("#beat-next").click();
  await expect(page.locator("#beat-02")).toBeVisible();
  await expect(page).toHaveURL(/#beat-02$/);

  await app.locator(".beat-tick").nth(6).click();
  await expect(page.locator("#beat-07")).toBeVisible();

  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#beat-08")).toBeVisible();
  await page.keyboard.press("ArrowLeft");
  await expect(page.locator("#beat-07")).toBeVisible();
  await page.keyboard.press("End");
  await expect(page.locator("#beat-12")).toBeVisible();
  await page.keyboard.press("Home");
  await expect(page.locator("#beat-01")).toBeVisible();

  // The stage tracks the active beat.
  await expect(page.locator(".oneway-stage")).toHaveAttribute("data-beat", "1");

  // aria-live announcement carries the caption.
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#beat-announce")).toContainText("Beat 2 of 12");
});

test("deep link: /demo/#beat-07 opens at beat seven", async ({ page }) => {
  await page.goto("/demo/#beat-07");
  await expect(page.locator("#beat-07")).toBeVisible();
  await expect(page.locator(".oneway-stage")).toHaveAttribute("data-beat", "7");
});

test("no-JS: the complete story renders in document order; controls stay hidden", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/demo/");
  for (let n = 1; n <= 12; n++) {
    await expect(page.locator(`#beat-${String(n).padStart(2, "0")}`)).toBeVisible();
  }
  await expect(page.locator("#stage-controls")).toBeHidden();
  // The stage's no-JS state is beat 12 — the complete frame.
  await expect(page.locator(".oneway-stage")).toHaveAttribute("data-beat", "12");
  await context.close();
});

test("reduced motion: stepping works as captioned stills", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/demo/");
  await page.locator("#beat-next").click();
  await expect(page.locator("#beat-02")).toBeVisible();
  await page.locator("#beat-rail .beat-tick").nth(4).click();
  await expect(page.locator("#beat-05")).toBeVisible();
  await expect(page.locator(".oneway-stage")).toHaveAttribute("data-beat", "5");
});
