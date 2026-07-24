// Install honesty gates:
//   1. The literal ban: the old squatted PyPI name must never appear in an
//      install command anywhere in the built output ("detent" is a different,
//      active package — installing it was the decisive naming collision).
//      The strings below are the banned literals, present here ONLY to
//      assert their absence.
//   2. Package-index commands appear only on /install/ inside the release
//      verification boundary, never as context-free marketing copy.
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const dist = fileURLToPath(new URL("../dist", import.meta.url));

function htmlFiles(dir: string): string[] {
  const out: string[] = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) out.push(...htmlFiles(join(dir, e.name)));
    else if (e.name.endsWith(".html")) out.push(join(dir, e.name));
  }
  return out;
}

const BANNED_INSTALLS = [
  "pip install detent",
  "uvx detent",
  "uv tool install detent",
  "pipx install detent",
];

// The ONE sanctioned exception: the rendered copy of ADR-0023 — the
// append-only decision record that QUOTES the squatted-package collision as
// the reason for the rename. It renders under a provenance banner; the
// historical record keeping the old name is the append-only discipline
// working as designed.
const ADR_0023 = /docs\/reference\/adr-0023-rename-to-irrevon\/index\.html$/;

test("literal ban: no install command for the old squatted package name", () => {
  for (const file of htmlFiles(dist)) {
    if (ADR_0023.test(file)) continue;
    const html = readFileSync(file, "utf8").toLowerCase();
    for (const banned of BANNED_INSTALLS) {
      expect(html.includes(banned), `${file} contains banned literal "${banned}"`).toBe(false);
    }
  }
});

test("package-index commands stay inside the verified release boundary", () => {
  const commands = [/pip install irrevon/, /uvx irrevon/, /uv tool install irrevon/, /pipx install irrevon/];
  for (const file of htmlFiles(dist)) {
    if (ADR_0023.test(file)) continue; // historical decision text, provenance-bannered
    const html = readFileSync(file, "utf8");
    for (const re of commands) {
      if (!re.test(html)) continue;
      // /install/ is the only page that may carry package-index commands.
      expect(file.replace(dist, ""), `package-index command ${re} outside /install/`).toMatch(
        /install\/index\.html$/,
      );
      const releaseBlock =
        html.match(/<[^>]*data-release-install[\s\S]*?<\/div>\s*<\/div>\s*<\/section>/)?.[0] ?? "";
      expect(releaseBlock, `release verification block missing around ${re} in ${file}`).toMatch(re);
    }
  }
});

test("/install/ requires release verification and keeps source setup first", async ({ page }) => {
  await page.goto("/install/");
  const release = page.locator("[data-release-install]");
  await expect(release).toBeVisible();
  await expect(release.locator(".release-chip")).toContainText("VERIFY RELEASE STATUS");
  await expect(release).toContainText("OIDC Trusted Publishing");
  await expect(release.getByRole("link", { name: "Status" })).toHaveAttribute("href", /\/status\/$/);
  // The source checkout section leads the page.
  const sections = page.locator("main section");
  await expect(sections.nth(1)).toContainText("Build and run locally");
  await expect(sections.nth(1)).toContainText("set -a && . ./.env && set +a");
});
