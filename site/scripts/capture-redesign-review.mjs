// One-off review capture for the One-Way Seat stage redesign: the stage panel
// at key beats, desktop + mobile, both themes for beat 12. Not a gate — a
// review artifact generator (writes shots/redesign-*.png, gitignored).
// Usage: node scripts/capture-redesign-review.mjs  (preview must be on :4977)
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const BASE = "http://localhost:4977";
mkdirSync(new URL("../shots", import.meta.url), { recursive: true });
const out = (name) => new URL(`../shots/${name}`, import.meta.url).pathname;

const browser = await chromium.launch();

async function capture(width, height, beat, theme, name) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.addInitScript((t) => localStorage.setItem("theme", t), theme);
  await page.goto(`${BASE}/demo/#beat-${String(beat).padStart(2, "0")}`);
  await page.waitForSelector(`.oneway-stage[data-beat="${beat}"]`);
  await page.waitForTimeout(400);
  await page.locator("#demo-app").screenshot({ path: out(name) });
  await page.close();
  console.log(`wrote shots/${name}`);
}

for (const beat of [1, 4, 5, 7, 8, 10, 12]) {
  await capture(1440, 1100, beat, "dark", `redesign-beat${String(beat).padStart(2, "0")}-desktop-dark.png`);
}
await capture(1440, 1100, 12, "light", "redesign-beat12-desktop-light.png");
for (const beat of [1, 8, 12]) {
  await capture(375, 900, beat, "dark", `redesign-beat${String(beat).padStart(2, "0")}-mobile-dark.png`);
}

await browser.close();
