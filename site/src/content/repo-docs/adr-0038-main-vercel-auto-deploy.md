---
title: "Vercel Git integration deploys the static site from protected main"
sourcePath: "docs/decisions/0038-main-vercel-auto-deploy.md"
sourceSha256: "89b614195a6bfcc4ae3fb9dd571ea532ba35bedc7c9fe5652bfc070ec8f05888"
syncedAt: "2026-07-24"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0038"
  status: "accepted (owner automatic-deployment directive, 2026-07-24)"
  date: "2026-07-24"
  supersedes: "ADR-0027's human-upload deployment mechanic"
---

## Context

ADR-0027 selected Vercel but required owner-built static uploads. The connected
project subsequently autodetected the repository root as Python, and its early
Git deployments failed; repository-level `git.deploymentEnabled: false` stopped
that noisy path. Manual production uploads then left the public alias behind
the reviewed default branch and without the repository's deployment-provenance
document.

Vercel's Git integration creates a production deployment when a commit reaches
the configured production branch. Its repository configuration can override
framework, install, build, output, header, and branch-deployment behavior. The
owner's 2026-07-24 directive requires the marketing site to rebuild from the
latest reviewed code automatically.

## Decision

The existing Vercel project remains connected to this repository, uses Node 24,
and treats protected `main` as its only automatic deployment branch. The root
`vercel.json` overrides the stale Python autodetection: it installs the locked
`site/` pnpm graph, runs the fail-closed site build wrapper, serves
`site/dist`, and carries the complete edge-header contract.

The build wrapper refuses Vercel Git builds unless the environment is
`production`, the Git ref is exactly `main`, and the source commit is a full
SHA. `git.deploymentEnabled` disables every branch and re-enables only `main`;
because Vercel resolves overlapping rules in favor of `true`, `main` matches
both rules and deploys while every other branch remains disabled.

This policy automates website deployment only. It does not push code to
`main`, merge pull requests, publish Python packages or GitHub Releases,
register benchmarks, run providers, or change the human gates on those acts.

## Alternatives

- **Continue manual static uploads:** rejected because the public alias already
  drifted behind source and an operator can silently omit a deployment.
- **Deploy every branch:** rejected because unreviewed preview deployments add
  a public surface and recreate the noisy failing-status path.
- **Add a GitHub Actions deploy workflow:** rejected because Vercel's native
  Git integration already binds deployments to commit metadata and avoids
  another token-bearing workflow.
- **Auto-publish every platform from `main`:** rejected because package,
  scientific, and provider publication have independent human gates.

## Consequences

After this change is reviewed and merged, every new `main` commit creates one
production-site build with Vercel Git metadata. `/version.json` can identify
the exact source commit, and the production smoke test validates the same
configuration used by the platform.

The repository-level Vercel configuration becomes a deployment-critical
contract. Root configuration changes select the complete site CI slice.
Preview branches do not receive automatic deployments.

## Risks

A Vercel project-level override could disagree with the committed contract, or
the Git connection/production branch could be changed outside the repository.
Release readiness therefore requires platform read-back plus a live
`/version.json` comparison after merge. The connector cannot make a stale
deployment current before the reviewed commit reaches `main`.

## Reopen trigger

Revisit if preview environments become an explicit reviewed requirement, the
site moves away from Vercel, Vercel branch-matching semantics change, or a
protected staged-promotion workflow becomes necessary.
