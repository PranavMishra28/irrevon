// Development screenshot harness (not a test): captures the routes at the
// BRIEF-mandated widths, themes, and reduced-motion for visual inspection.
// Output goes to web/.dev-screens/ (gitignored).
import { mkdirSync } from "node:fs";
import { chromium } from "@playwright/test";

const BASE = process.env.BASE_URL ?? "http://localhost:5199";
const OUT = new URL("../.dev-screens/", import.meta.url).pathname;

const routes = process.argv[2]
  ? [process.argv[2]]
  : [
      "/learn/start",
      "/learn/identity",
      "/learn/state",
      "/learn/tiers",
      "/effects",
      "/demo",
      "/health",
      "/attention",
      "/findings",
      "/adapters",
      "/bench",
      "/taxonomy",
    ];

const widths = process.env.WIDTHS
  ? process.env.WIDTHS.split(",").map(Number)
  : [1280, 1440, 1920];

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();

for (const theme of ["light", "dark"]) {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of routes) {
      await page.goto(BASE + route, { waitUntil: "networkidle" });
      await page.evaluate((t) => {
        document.documentElement.setAttribute("data-theme", t);
        return document.fonts.ready;
      }, theme);
      await page.waitForTimeout(120);
      const name = `${route.replaceAll("/", "_").replace(/^_/, "") || "root"}-${width}-${theme}.png`;
      await page.screenshot({ path: OUT + name, fullPage: true });
      console.log(name);
    }
  }
  await context.close();
}

await browser.close();
