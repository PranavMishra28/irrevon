---
id: ADR-0038
title: Vercel Git integration permits main-only static-site deployments
status: accepted (owner automatic-deployment directive, 2026-07-24)
date: 2026-07-24
supersedes: ADR-0027's human-upload deployment mechanic
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
owner's 2026-07-24 directive requires the marketing site to rebuild
automatically from code that reaches `main`.

## Decision

The existing Vercel project remains connected to this repository and uses Node
24. Repository policy makes `main` the only branch eligible for an automatic
deployment. The root `vercel.json` overrides the stale Python autodetection: it
installs the locked `site/` pnpm graph, runs the fail-closed site build wrapper,
serves `site/dist`, and carries the complete edge-header contract.

The build wrapper refuses Vercel Git builds unless the environment is
`production`, the Git ref is exactly `main`, and the source commit is a full
SHA. `git.deploymentEnabled` disables every branch and re-enables only `main`;
because Vercel resolves overlapping rules in favor of `true`, `main` matches
both rules and deploys while every other branch remains disabled.

Platform activation remains an owner action. The owner must confirm that the
Vercel Production Branch is `main` and reactivate the project after merging this
reviewed change. The authenticated 2026-07-24 read-back confirmed Node 24 and a
paused project but did not expose the Production Branch, so neither activation
nor that branch setting is inferred from repository configuration.

Vercel does not consume GitHub's `ci-required` result. The repository ruleset is
the review boundary, and its 2026-07-24 read-back still showed an always-allowed
repository-role bypass. That bypass must be removed before every commit reaching
`main` can truthfully be described as reviewed or CI-validated.

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

After this change is reviewed and merged, and after the owner verifies the
Production Branch and reactivates the project, each eligible `main` commit
creates a production-site build with Vercel Git metadata. `/version.json` can
identify the exact source commit, and the production smoke test validates the
same configuration used by the platform.

The repository-level Vercel configuration becomes a deployment-critical
contract. Root configuration changes select the complete site CI slice.
Preview branches do not receive automatic deployments.

## Risks

A Vercel project-level override could disagree with the committed contract, the
Git connection/Production Branch could change outside the repository, or a
GitHub bypass actor could place an unvalidated commit on `main`. Release
readiness therefore requires removal of the ruleset bypass, platform read-back,
and a live `/version.json` comparison after merge. Repository configuration
cannot reactivate a paused project.

## Reopen trigger

Revisit if preview environments become an explicit reviewed requirement, the
site moves away from Vercel, Vercel branch-matching semantics change, or a
protected staged-promotion workflow becomes necessary.
