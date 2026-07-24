// Review screenshots: every built page (inventory derived from dist/) at
// 1440/1024/768/390/320 × light/dark, plus reduced-motion and forced-color
// page's stepped states. Written to shots/ (gitignored) for the premium-bar
// visual review.
import { test } from "@playwright/test";
import { ALL_PAGES } from "./pages";

const VIEWPORTS = [
  { name: "1440", width: 1440, height: 900 },
  { name: "1024", width: 1024, height: 768 },
  { name: "768", width: 768, height: 1024 },
  { name: "390", width: 390, height: 844 },
  { name: "320", width: 320, height: 720 },
];

const slugOf = (path: string) => (path === "/" ? "home" : path.replaceAll("/", "-").replace(/^-|-$/g, "").replace(".html", ""));

for (const path of ALL_PAGES) {
  for (const vp of VIEWPORTS) {
    for (const theme of ["light", "dark"] as const) {
      test(`shot: ${path} ${vp.name} ${theme}`, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: vp.width, height: vp.height },
          colorScheme: theme,
        });
        const page = await context.newPage();
        await page.goto(`http://localhost:4977${path}`, { waitUntil: "networkidle" });
        const slug = slugOf(path);
        await page.screenshot({ path: `shots/${slug}-${vp.name}-${theme}.png`, fullPage: true });
        if (vp.name === "1440") {
          await page.screenshot({ path: `shots/${slug}-${vp.name}-${theme}-top.png` });
        }
        await context.close();
      });
    }
  }
}

// Reduced-motion review: the demo page's stepped states must read as
// complete captioned stills.
for (const beat of ["01", "05", "10", "12"]) {
  test(`shot: /demo/ reduced-motion beat ${beat}`, async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    await page.goto(`http://localhost:4977/demo/#beat-${beat}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(200);
    await page.screenshot({ path: `shots/demo-rm-beat${beat}.png` });
    await context.close();
  });
}

for (const path of ["/", "/docs/", "/demo/"]) {
  test(`shot: ${path} forced-colors`, async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 1024, height: 768 },
      forcedColors: "active",
    });
    const page = await context.newPage();
    await page.goto(`http://localhost:4977${path}`, { waitUntil: "networkidle" });
    await page.screenshot({ path: `shots/${slugOf(path)}-forced-colors.png`, fullPage: true });
    await context.close();
  });
}
