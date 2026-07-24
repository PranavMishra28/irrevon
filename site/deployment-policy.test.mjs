import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import test from "node:test";

const repositoryRoot = fileURLToPath(new URL("../", import.meta.url));
const config = JSON.parse(
  readFileSync(new URL("../vercel.json", import.meta.url), "utf8"),
);

test("Vercel deploys protected main and no other branch", () => {
  assert.deepEqual(config.git?.deploymentEnabled, {
    "*": false,
    main: true,
  });
  assert.equal(config.framework, "astro");
  assert.equal(config.outputDirectory, "site/dist");
  assert.equal(
    config.installCommand,
    "corepack enable && pnpm --dir site install --frozen-lockfile",
  );
  assert.equal(config.buildCommand, "bash scripts/vercel-build.sh");
});

const runVercelBuild = (overrides) =>
  spawnSync("bash", ["scripts/vercel-build.sh"], {
    cwd: repositoryRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      VERCEL: "1",
      VERCEL_ENV: "production",
      VERCEL_GIT_COMMIT_REF: "main",
      VERCEL_GIT_COMMIT_SHA: "a".repeat(40),
      ...overrides,
    },
  });

test("Vercel build wrapper refuses non-production and non-main builds", () => {
  const preview = runVercelBuild({ VERCEL_ENV: "preview" });
  assert.notEqual(preview.status, 0);
  assert.match(preview.stderr, /VERCEL_ENV=production/);

  const branch = runVercelBuild({ VERCEL_GIT_COMMIT_REF: "feature" });
  assert.notEqual(branch.status, 0);
  assert.match(branch.stderr, /VERCEL_GIT_COMMIT_REF=main/);
});

test("Vercel build wrapper refuses absent, short, or malformed source commits", () => {
  for (const commit of ["", "abcdef0", "z".repeat(40)]) {
    const result = runVercelBuild({ VERCEL_GIT_COMMIT_SHA: commit });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /full VERCEL_GIT_COMMIT_SHA/);
  }
});
