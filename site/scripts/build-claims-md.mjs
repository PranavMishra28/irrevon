// Renders site/CLAIMS.md (the committed claim → source table) from the single
// claims registry in src/data/claims.ts. `--check` fails CI when the committed
// table drifts from the registry. Node 24 type-stripping loads the .ts directly.
//
// Usage: node scripts/build-claims-md.mjs [--check]

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = join(here, "..");
const outFile = join(siteRoot, "CLAIMS.md");
const check = process.argv.includes("--check");

const { claims } = await import("../src/data/claims.ts");

const badgeText = {
  recorded: "RECORDED ARTIFACT",
  conceptual: "CONCEPTUAL",
  preregistered: "PREREGISTERED METHODOLOGY — NO RESULTS YET",
};

const esc = (s) => s.replaceAll("|", "\\|").replaceAll("\n", " ");

const rows = Object.entries(claims)
  .map(([id, c]) => {
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) {
      throw new TypeError(`claims-md: claim id cannot form a stable anchor: ${id}`);
    }
    return `| <a id="claim-${id}" name="claim-${id}"></a>\`${id}\` | ${esc(c.claim)} | ${esc(c.source)} | \`[${c.label}]\` | ${c.badge ? badgeText[c.badge] : "—"} |`;
  })
  .join("\n");

const doc = `# Site claims registry

GENERATED from [\`src/data/claims.ts\`](src/data/claims.ts) by
\`scripts/build-claims-md.mjs\` — do not edit by hand (\`pnpm claims:md\` regenerates;
\`--check\` gates CI). Every claim-bearing section on the site references an id from
this table; epistemic labels per master doc §0.

${Object.keys(claims).length} claims.

| id | claim | source | label | badge |
|---|---|---|---|---|
${rows}
`;

if (check) {
  let current = "";
  try {
    current = readFileSync(outFile, "utf8");
  } catch {
    console.error("claims-md: CLAIMS.md missing — run `pnpm claims:md`");
    process.exit(1);
  }
  if (current !== doc) {
    console.error("claims-md: DRIFT between claims.ts and CLAIMS.md — run `pnpm claims:md`");
    process.exit(1);
  }
  console.log("claims-md: CLAIMS.md matches the registry");
} else {
  writeFileSync(outFile, doc);
  console.log(`claims-md: wrote ${outFile} (${Object.keys(claims).length} claims)`);
}
