// Renders repository documents into the site's content collection
// (src/content/repo-docs/) per docs-manifest.json — the claims-registry
// sync pattern generalized. The repository copy stays canonical; every
// rendered file carries generated provenance frontmatter (sourcePath +
// sourceSha256) and a provenance banner renders it on the page.
//
// Bodies are transformed mechanically only: the source's own YAML
// frontmatter (ADRs) is lifted into structured fields; nothing else is
// touched. Repo-relative links are rewritten at BUILD time (see
// scripts/remark-repo-links.mjs) so the committed copies never embed a
// repository URL.
//
// `--check` re-derives every file and fails on any byte drift (wired into
// `pnpm check`), so a hand edit of a rendered copy cannot land. syncedAt
// is preserved while the source hash is unchanged, keeping --check
// deterministic.
//
// Usage: node scripts/sync-docs.mjs [--check]

import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = join(here, "..");
const repoRoot = join(siteRoot, "..");
const outDir = join(siteRoot, "src", "content", "repo-docs");
const check = process.argv.includes("--check");

const manifest = JSON.parse(readFileSync(join(siteRoot, "docs-manifest.json"), "utf8"));

const sha256 = (text) => createHash("sha256").update(text).digest("hex");
const yamlStr = (s) => `"${String(s).replaceAll("\\", "\\\\").replaceAll('"', '\\"')}"`;

/** Naive single-document YAML frontmatter split (the ADR files use plain
 *  `key: value` lines only — no nesting, no multiline scalars). */
function splitFrontmatter(text) {
  if (!text.startsWith("---\n")) return { meta: {}, body: text };
  const end = text.indexOf("\n---\n", 4);
  if (end === -1) return { meta: {}, body: text };
  const meta = {};
  for (const line of text.slice(4, end).split("\n")) {
    const m = line.match(/^([A-Za-z][\w-]*):\s*(.*)$/);
    if (m) meta[m[1]] = m[2].trim();
  }
  return { meta, body: text.slice(end + 5).replace(/^\n+/, "") };
}

function deriveTitle(entry, meta, body) {
  if (entry.title) return entry.title;
  if (meta.title) return meta.title;
  const h1 = body.match(/^#\s+(.+)$/m);
  if (h1) return h1[1].trim();
  throw new Error(`sync-docs: no title derivable for ${entry.source}`);
}

function renderExpected(entry, existing) {
  const raw = readFileSync(join(repoRoot, entry.source), "utf8");
  const hash = sha256(raw);
  const { meta, body } = splitFrontmatter(raw);
  const title = deriveTitle(entry, meta, body);
  const renderTitle = !/^#\s+/.test(body);

  // Keep the previous syncedAt while the source is byte-identical so
  // --check stays deterministic; a content change stamps a new date.
  let syncedAt = new Date().toISOString().slice(0, 10);
  if (existing) {
    const prevHash = existing.match(/^sourceSha256: "([0-9a-f]{64})"$/m)?.[1];
    const prevDate = existing.match(/^syncedAt: "([0-9-]+)"$/m)?.[1];
    if (prevHash === hash && prevDate) syncedAt = prevDate;
  }

  const fm = [
    "---",
    `title: ${yamlStr(title)}`,
    ...(entry.description ? [`description: ${yamlStr(entry.description)}`] : []),
    `sourcePath: ${yamlStr(entry.source)}`,
    `sourceSha256: ${yamlStr(hash)}`,
    `syncedAt: ${yamlStr(syncedAt)}`,
    `section: ${yamlStr(entry.section)}`,
    `renderTitle: ${renderTitle}`,
    ...(entry.badge ? [`badge: ${yamlStr(entry.badge)}`] : []),
  ];
  if (meta.id) {
    fm.push("adr:");
    fm.push(`  id: ${yamlStr(meta.id)}`);
    if (meta.status) fm.push(`  status: ${yamlStr(meta.status)}`);
    if (meta.date) fm.push(`  date: ${yamlStr(meta.date)}`);
    if (meta.supersedes) fm.push(`  supersedes: ${yamlStr(meta.supersedes)}`);
  }
  fm.push("---", "");
  return fm.join("\n") + "\n" + body;
}

mkdirSync(outDir, { recursive: true });
const wanted = new Map();
let failed = false;

for (const entry of manifest.render) {
  const outFile = join(outDir, `${entry.slug}.md`);
  const existing = existsSync(outFile) ? readFileSync(outFile, "utf8") : null;
  const expected = renderExpected(entry, existing);
  wanted.set(`${entry.slug}.md`, true);
  if (check) {
    if (existing !== expected) {
      console.error(`sync-docs: DRIFT in ${entry.slug}.md (source ${entry.source}) — run \`pnpm sync:docs\``);
      failed = true;
    }
  } else if (existing !== expected) {
    writeFileSync(outFile, expected);
    console.log(`sync-docs: wrote ${entry.slug}.md`);
  }
}

// The directory is generated: stray files are drift too.
for (const f of readdirSync(outDir)) {
  if (!wanted.has(f)) {
    if (check) {
      console.error(`sync-docs: stray file ${f} in src/content/repo-docs/`);
      failed = true;
    } else {
      rmSync(join(outDir, f));
      console.log(`sync-docs: removed stray ${f}`);
    }
  }
}

// llms.txt (Answer.AI convention; Antithesis-style machine-readable docs
// index) — generated from the same manifest + guides, drift-gated like the
// rendered docs. Root-relative links only: nothing committed embeds an origin.
function renderLlmsTxt() {
  const lines = [
    "# Irrevon",
    "",
    "> A benchmark drafted for preregistration (IrrevonBench) and reference reconciliation",
    "> engine for irreversible AI-agent actions. Pre-release; no benchmark",
    "> results exist; confirmatory runs are mechanically refused before the",
    "> human preregistration freeze.",
    "",
    "## Product",
    "",
    "- [How it works](/how-it-works/): the mental model — read first",
    "- [Engine](/platform/): what runs today",
    "- [Benchmark](/benchmark/): the measurement method and its status",
    "- [Demo](/demo/): the recorded flagship contrast run",
    "- [Install](/install/): local quickstart",
    "",
    "## Guides",
    "",
  ];
  for (const f of readdirSync(join(siteRoot, "src", "content", "guides")).sort()) {
    if (!f.endsWith(".md")) continue;
    const raw = readFileSync(join(siteRoot, "src", "content", "guides", f), "utf8");
    const title = raw.match(/^title:\s*"?([^"\n]+)"?$/m)?.[1] ?? f.replace(/\.md$/, "");
    lines.push(`- [${title}](/docs/${f.replace(/\.md$/, "")}/)`);
  }
  lines.push("", "## Reference (rendered repository documents)", "");
  for (const entry of manifest.render) {
    const raw = readFileSync(join(repoRoot, entry.source), "utf8");
    const title =
      entry.title ??
      splitFrontmatter(raw).meta.title ??
      raw.match(/^#\s+(.+)$/m)?.[1]?.trim() ??
      entry.slug;
    lines.push(`- [${title}](/docs/reference/${entry.slug}/): source ${entry.source}`);
  }
  lines.push("");
  return lines.join("\n");
}

const llmsPath = join(siteRoot, "public", "llms.txt");
const llmsExpected = renderLlmsTxt();
const llmsExisting = existsSync(llmsPath) ? readFileSync(llmsPath, "utf8") : null;
if (check) {
  if (llmsExisting !== llmsExpected) {
    console.error("sync-docs: DRIFT in public/llms.txt — run `pnpm sync:docs`");
    failed = true;
  }
} else if (llmsExisting !== llmsExpected) {
  writeFileSync(llmsPath, llmsExpected);
  console.log("sync-docs: wrote public/llms.txt");
}

if (check) {
  if (failed) process.exit(1);
  console.log(`sync-docs: ${manifest.render.length} rendered docs match their repository sources (+ llms.txt)`);
} else {
  console.log(`sync-docs: ${manifest.render.length} docs in sync (+ llms.txt)`);
}
