// Generates the CLI reference guide from the engine's own help text —
// captured, never paraphrased. Runs `uv run irrevon --help` (and each
// subcommand's --help) at the repository root and writes the committed
// src/content/guides/cli-reference.md with the captured text verbatim in
// code blocks.
//
// `--check` re-captures and fails on drift when the engine toolchain is
// available; where it is not (a Node-only CI lane), it falls back to the
// tamper-evidence check: the committed body must match the sha256 recorded
// in its own frontmatter, so a hand edit still fails the gate. Full
// re-capture is the local, engine-present act.
//
// Usage: node scripts/sync-cli-reference.mjs [--check]

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = join(here, "..");
const repoRoot = join(siteRoot, "..");
const outFile = join(siteRoot, "src", "content", "guides", "cli-reference.md");
const check = process.argv.includes("--check");

const SUBCOMMANDS = ["init", "doctor", "demo", "inspect"];
const sha256 = (text) => createHash("sha256").update(text).digest("hex");

function capture(args) {
  return execFileSync("uv", ["run", "irrevon", ...args], {
    cwd: repoRoot,
    encoding: "utf8",
    env: { ...process.env, COLUMNS: "88" },
    stdio: ["ignore", "pipe", "pipe"],
  }).trimEnd();
}

function buildBody() {
  const top = capture(["--help"]);
  const sections = SUBCOMMANDS.map((sub) => {
    const text = capture([sub, "--help"]);
    return `## \`irrevon ${sub}\`\n\n\`\`\`text\n${text}\n\`\`\``;
  });
  return [
    "Captured verbatim from the CLI's own `--help` output — the engine is the",
    "single source for flags and semantics; this page never paraphrases them.",
    "Regenerate with `pnpm sync:cli` where the engine toolchain (uv) runs.",
    "",
    "## `irrevon`",
    "",
    "```text",
    top,
    "```",
    "",
    sections.join("\n\n"),
    "",
  ].join("\n");
}

function renderFile(body) {
  const fm = [
    "---",
    'title: "CLI reference"',
    'description: "Every irrevon subcommand, captured verbatim from the CLI\'s own --help output — generated, drift-gated, never paraphrased."',
    "order: 2",
    "generated:",
    '  command: "uv run irrevon --help (+ per-subcommand --help)"',
    `  capturedSha256: "${sha256(body)}"`,
    "claims:",
    "  - quickstart-real",
    "---",
    "",
  ].join("\n");
  return fm + body;
}

function tamperCheck() {
  if (!existsSync(outFile)) {
    console.error("sync-cli-reference: committed cli-reference.md missing — run `pnpm sync:cli`");
    process.exit(1);
  }
  const current = readFileSync(outFile, "utf8");
  const recorded = current.match(/capturedSha256: "([0-9a-f]{64})"/)?.[1];
  const body = current.slice(current.indexOf("---", 4) + 4).replace(/^\n/, "");
  if (!recorded || sha256(body) !== recorded) {
    console.error("sync-cli-reference: committed body does not match its recorded capture hash — regenerate with `pnpm sync:cli`");
    process.exit(1);
  }
  console.log("sync-cli-reference: tamper-evidence check passed (engine toolchain unavailable for full re-capture)");
}

let body;
try {
  body = buildBody();
} catch {
  if (check) {
    tamperCheck();
    process.exit(0);
  }
  console.error("sync-cli-reference: could not run `uv run irrevon --help` — the engine toolchain is required to (re)generate");
  process.exit(1);
}

const expected = renderFile(body);
const current = existsSync(outFile) ? readFileSync(outFile, "utf8") : null;

if (check) {
  if (current !== expected) {
    console.error("sync-cli-reference: DRIFT between the CLI's help output and the committed reference — run `pnpm sync:cli`");
    process.exit(1);
  }
  console.log("sync-cli-reference: committed reference matches the CLI's --help output");
} else if (current !== expected) {
  writeFileSync(outFile, expected);
  console.log("sync-cli-reference: wrote cli-reference.md");
} else {
  console.log("sync-cli-reference: cli-reference.md in sync");
}
