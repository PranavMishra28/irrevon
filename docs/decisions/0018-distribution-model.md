---
id: ADR-0018
title: Distribution model — single PyPI package with embedded workbench assets, GitHub-and-Zenodo-only infrastructure, zero recurring cost
status: accepted (ratified in writing by the owner, 2026-07-21)
date: 2026-07-21
supersedes: —
---

## Context

Detent ships (per master doc §5.1–§5.2, §10, §15 M8/M9): a Python engine+SDK+CLI+bench
(ADR-0013), a Vite SPA workbench served as static assets by the CLI (ADR-0016),
language-neutral JSON Schemas, and a capability-declaration registry ("lightweight
companion", §5.1). Constraints: solo maintainer at ~10 h/wk; no revenue-bearing activity
pending external clearances (§13); near-zero budget; <30-minute stranger integration (§10);
no hosted SaaS, no billing (§5.4); publishing is human-gated (execution-plan public-release
gate). Verified facts (2026-07): PyPI default limits 100 MB/file, 10 GB/project; GitHub
Actions standard runners free on public repos; GitHub Pages free on public repos (1 GB
site / 100 GB-mo soft); GHCR free for public images vs Docker Hub 100 pulls/6h/IP
unauthenticated; GitHub Releases 2 GiB/file, unlimited total; Zenodo 50 GB/record free with
DOI; AWS Free Tier (post-2025-07) is a 6-month expiring credit trial with account
auto-closure; hatchling `artifacts` is the current correct mechanism for shipping built
gitignored web assets in a wheel (force-include breaks editable installs).

## Decision

Ship ONE PyPI distribution, `detent` (name pending the P2 screen; packaging metadata
inherits ADR-011's fallback): engine, SDK, CLI (`[project.scripts] detent =
"detent.cli:main"`), bench harness, stub destination, registry data, and the prebuilt
`web/dist` embedded via hatchling `artifacts` and read with `importlib.resources` —
prebuilt assets included in both wheel and sdist so no install path requires Node. Single
SemVer 0.x version for the distribution; payload compatibility is carried by the existing
per-payload `schema_version`, independent of package version. Registry stays an in-repo
`registry/` directory shipped as package data — no separate repo, no hosted registry.
Containers: compose.yaml with digest-pinned Postgres only; no published Detent image at
v0.1; the M7/M8 benchmark-repro image publishes to GHCR (human-gated). Install paths:
uvx / uv tool install / pipx / pip; uninstall is documented as package removal +
`docker compose down -v` + deleting the project-local files (no global state). Benchmark
reproduction ships BOTH legs: committed uv.lock (`uv sync --locked` from the signed tag)
and the digest-pinned container; canonical run artifacts go to GitHub Releases (working)
and Zenodo (archival DOI) — benchmark run evidence is never parked in expiring CI
artifacts (they may carry transport copies only; the permanent record is the append-only
result store). Docs: in-repo markdown until M8, then Material for MkDocs on GitHub Pages;
no custom domain; no docs SaaS. Infrastructure ruling: every hosting surface is local,
static, or GitHub/Zenodo-free; AWS and all cloud tiers rejected pre-G0. Total recurring
cost: $0/month through public release.

## Alternatives

- core+cli+bench package split — 3× release/QA/naming cost for zero consumers; Airflow-style
  splits are an at-scale endgame with measured triggers, not a start state.
- Separate registry repository — §5.1's companion is a data directory + schema; a second
  repo adds sync cost before any external contributor exists.
- Published Docker image at v0.1 — nothing daemonizes; wheel+CLI covers every user.
- Docker Hub — unauthenticated pull throttling breaks CI consumers; GHCR is free/unthrottled.
- Read the Docs / Docusaurus / custom domain — external platforms, Node-outside-web/, and
  recurring cost for nothing GitHub Pages + MkDocs doesn't provide.
- AWS Free Tier (and GCP/Azure equivalents) — expiring-trial structure unfit for a
  long-lived reproducible benchmark; nothing in the design needs a server.
- Kubernetes / Kafka / microservices — orchestration, an event bus, and service splits for
  a single-process deterministic core with one Postgres; rejected with the trigger
  "G0-gated product with multi-service scale evidence," never pre-G0.

## Consequences

Easier: one install name and one version to document, test (the clean-env quickstart
meta-test exercises the real wheel), and release; the stranger test's install step is one
command; $0 infrastructure means no billing coupling to the clearance constraints. Harder:
wheel builds acquire a frontend-build ordering dependency (release pipeline runs web-build
first — CI-enforced); single version means a workbench-only fix bumps the whole
distribution (accepted at this scale). Conformance: the M8 release pipeline (trusted
publishing, SBOM, attestations, immutable releases) applies to this one artifact.

## Risks

GitHub free-for-public policy shifts (Actions/GHCR/Pages) — GHCR is the only surface with
an explicit "for now"; fallback (release-asset image tarballs, docs-in-repo) is free. PyPI
name collision at the P2 screen — ADR-011 fallback renames the package. Asset-bundle growth
breaking editable-install DX — bounded by the degrade-gracefully serve path.

## Reopen trigger

Any of: an external consumer demonstrates install pain extras cannot fix (split trigger);
external registry contributions want decoupled releases; GHCR announces pricing; Pages
bandwidth soft limit approached; G0 gate + external clearances (opens the hosted-infra
question under a new ADR); PyPI name screen fails.
