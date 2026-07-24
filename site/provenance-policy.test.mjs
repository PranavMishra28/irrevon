import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import test from "node:test";

const { claims } = await import("./src/data/claims.ts");

const importConfig = (commit) => {
  const env = {
    ...process.env,
    SITE_ORIGIN: "https://site.invalid",
    SITE_REPO_URL: "https://github.com/example/irrevon",
    VERCEL_ENV: "production",
  };
  delete env.VERCEL_GIT_COMMIT_SHA;
  if (commit !== undefined) env.VERCEL_GIT_COMMIT_SHA = commit;
  return spawnSync(
    process.execPath,
    ["--input-type=module", "--eval", "await import('./astro.config.mjs')"],
    { cwd: import.meta.dirname, env, encoding: "utf8" },
  );
};

test("production configuration fails closed without a full deployment commit", () => {
  for (const candidate of [undefined, "not-a-commit", "abcdef0"]) {
    const result = importConfig(candidate);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /production builds require VERCEL_GIT_COMMIT_SHA/);
  }
});

test("generated claims registry exposes one stable named anchor per claim", () => {
  const registry = readFileSync(new URL("./CLAIMS.md", import.meta.url), "utf8");
  const anchors = [
    ...registry.matchAll(/<a id="(claim-[a-z0-9-]+)" name="\1"><\/a>/g),
  ].map((match) => match[1]);
  assert.equal(anchors.length, Object.keys(claims).length);
  assert.equal(new Set(anchors).size, anchors.length);
  for (const id of Object.keys(claims)) assert.ok(anchors.includes(`claim-${id}`));
});
