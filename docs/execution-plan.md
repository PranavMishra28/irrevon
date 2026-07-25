# Project status and release roadmap

This is the current roadmap for users, contributors, and release reviewers.
Historical implementation phases are archived in
[history/execution-plan-pre-implementation.md](history/execution-plan-pre-implementation.md).
The machine-readable status is [project-status.json](project-status.json) and
`make public-truth` checks the primary public surfaces against it.

## Current release posture

Irrevon is public, Apache-2.0-licensed **Alpha software**. Version `0.1.0` is
available from [PyPI](https://pypi.org/project/irrevon/0.1.0/) and its
[immutable GitHub Release](https://github.com/PranavMishra28/irrevon/releases/tag/v0.1.0).
Source builds,
the deterministic flagship demo, the single-writer engine and worker, the
loopback read-only Workbench, synthetic provider-contract tests, the benchmark
development harness, and wheel/sdist construction are implemented.

No confirmatory benchmark result, preregistration freeze, or live-provider
observation exists. The Stripe and EasyPost adapters are
credential-gated drafts and have never been live-called. The evaluated runtime
boundary is self-hosted and single-writer, but it is not yet a supported
production topology; multi-writer leasing is not implemented.
The static website is deployed from protected `main`.

## What a source user can do now

- Clone the public repository and reproduce the deterministic PostgreSQL demo.
- Run unit, property, process-kill, integration, browser, accessibility, and
  benchmark known-answer tests.
- Inspect synthetic evidence in the Workbench or connect it to the local
  loopback read surface.
- Install `irrevon==0.1.0` or independently inspect its wheel, sdist,
  checksums, SPDX SBOM, and GitHub attestations.
- Exercise the reference destination and synthetic Stripe/EasyPost transports.
- Contribute through pull requests under Apache-2.0 with DCO 1.1 sign-off.

## Supported and unsupported boundaries

| Area | Supported now | Not claimed |
|---|---|---|
| Runtime | Evaluated boundary: at most one active writer, PostgreSQL 17, continuous reconciliation worker | Supported production ingress/topology, multi-writer HA, hosted control plane, production readiness |
| Evidence UI | Loopback-only, GET/HEAD-only, SELECT-only Workbench with digested upstream identifiers | Remote administrative console, browser-side mutation, authenticated multi-user service |
| Destinations | Deterministic reference destination; draft sandbox-only Stripe C1/EasyPost C2 code under synthetic tests | Qualified live provider semantics, production credentials, provider conformance evidence |
| Benchmark | Public synthetic development fixtures, harness, causal-history and metric cross-checks | Frozen registration, sealed confirmatory run, independent reproduction, scientific validation |
| Distribution | Published PyPI wheel/sdist, immutable GitHub Release, checksums, SPDX SBOM, GitHub attestations, OIDC Trusted Publishing, and clean-install proof | Stable pre-1.0 APIs or a scientific-results publication |

## Repository-local launch gates

These are enforced by `make launch-audit` and CI:

1. public-status, documentation, community, DCO, legal, and claims consistency;
2. secret/history scanning plus targeted current-tree privacy checks;
3. schema, ADR, generated-document, asset, and dependency-notice integrity;
4. strict Python, package-content, provider-transport, and security tests;
5. Workbench and site lint, browser, accessibility, responsive, link, and
   no-external-request tests;
6. deterministic benchmark integrity and known-answer checks;
7. non-publishing release dry run, checksums, SBOM, and provenance configuration;
8. explicit refusal to claim a production profile until topology, fresh-cluster
   restore, catch-up sweeps, and supervisor/container evidence exist.

## Remaining owner-only gates

Repository automation deliberately cannot complete these actions:

- obtain any required external clearance or legal/trademark review;
- choose and provision a real PostgreSQL deployment and secret manager;
- review current provider terms, complete ADR-0010/ADR-0012 spikes, and authorize
  sandbox observations;
- freeze Stage A or Stage B, timestamp registrations, or run confirmatory work;
- maintain repository rulesets, security settings, protected environments,
  immutable releases, and the main-only Vercel project;

Every item is independent: source users do not need a hosted account or hosted
PostgreSQL service to run the demo.

## Roadmap

### R1 — source launch (complete)

The repository-local gates are complete, outside contributions are accepted,
and claims remain aligned with synthetic evidence. This milestone did not
generate scientific results.

### R2 — provider qualification

After owner authorization, run bounded sandbox spikes, record sanitized
provider fixtures, ratify ADR-0010/ADR-0012, and update declarations only from
observed evidence. Draft adapters remain drafts until this closes.

### R3 — benchmark freeze and execution

Independent reviewers assess the Stage-A package; the owner freezes and
timestamps registrations before any confirmatory observation. Stage B then
pins provider artifacts and holdout commitments. Results are published whether
they favor Irrevon or falsify it.

### R4 — distribution (complete for v0.1.0)

The owner registered the PyPI trusted-publisher binding and protected GitHub
release environment, pushed the version-matching annotated tag, reviewed the
artifacts, and authorized publication. The workflow produced checksums, an SPDX
SBOM, GitHub attestations, immutable GitHub assets, and PyPI artifacts without a
long-lived publishing token.

## Version and compatibility

The published version is `0.1.0`: an initial public Alpha whose
interfaces are explicitly pre-1.0. Compatibility, deprecation, migration, and
rollback rules are in [operations.md](operations.md#compatibility-versioning-and-deprecation).
Release procedure and verification are in
[release-process.md](release-process.md).
