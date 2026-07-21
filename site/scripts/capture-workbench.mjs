// Captures workbench product imagery for the marketing site from the running
// web/ dev server (read-only usage) at the pinned 1440×900 viewport, both
// themes. The fixture-backed workbench renders the recorded seed-777 artifact;
// the SYNTHETIC FIXTURE banner is deliberately kept in frame (RD5 §5.3).
//
// Usage: WEB_URL=http://localhost:5199 node scripts/capture-workbench.mjs

import { mkdirSync } from "node:fs";
import { chromium } from "@playwright/test";

const WEB_URL = process.env.WEB_URL ?? "http://localhost:5199";
const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";

const shots = [
  { route: "/effects", name: "workbench-effects" },
  { route: `/effects/${FLAGSHIP}`, name: "workbench-inspect" },
];

mkdirSync("public/images", { recursive: true });

const browser = await chromium.launch();
for (const theme of ["light", "dark"]) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: theme,
  });
  await context.addInitScript((t) => {
    localStorage.setItem("detent.theme", t);
  }, theme);
  const page = await context.newPage();
  for (const s of shots) {
    await page.goto(`${WEB_URL}${s.route}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(800);
    await page.screenshot({ path: `public/images/${s.name}-${theme}.png` });
    console.log(`captured ${s.name}-${theme}.png`);
  }
  await context.close();
}
await browser.close();
