// Review screenshots: 1440/768/375 × light/dark for every page, written to
// shots/ (gitignored) for the premium-bar visual review.
import { test } from "@playwright/test";
import { PAGES } from "./pages";

const VIEWPORTS = [
  { name: "1440", width: 1440, height: 900 },
  { name: "768", width: 768, height: 1024 },
  { name: "375", width: 375, height: 812 },
];

for (const path of PAGES) {
  for (const vp of VIEWPORTS) {
    for (const theme of ["light", "dark"] as const) {
      test(`shot: ${path} ${vp.name} ${theme}`, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: vp.width, height: vp.height },
          colorScheme: theme,
        });
        const page = await context.newPage();
        await page.goto(`http://localhost:4977${path}`, { waitUntil: "networkidle" });
        const slug = path === "/" ? "home" : path.replaceAll("/", "");
        await page.screenshot({ path: `shots/${slug}-${vp.name}-${theme}.png`, fullPage: true });
        // Viewport-sized review slices at reading scale (top + one mid-scroll).
        if (vp.name === "1440") {
          await page.screenshot({ path: `shots/${slug}-${vp.name}-${theme}-top.png` });
          await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight * 0.33));
          await page.waitForTimeout(120);
          await page.screenshot({ path: `shots/${slug}-${vp.name}-${theme}-mid.png` });
        }
        await context.close();
      });
    }
  }
}
