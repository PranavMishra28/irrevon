# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/) after the first release.

## [Unreleased]

No changes yet.

## [0.1.0] - pending publication

### Added

- Continuous single-writer reconciliation worker and loopback read-only
  Workbench.
- Draft Stripe C1 and EasyPost C2 adapters with sandbox/test-key gates and
  synthetic conformance tests.
- IrrevonBench development harness, causal histories, conformance checking, and
  public synthetic fixtures.
- Apache-2.0 external contribution path with mandatory DCO sign-off.
- Executable, non-publishing release dry run and launch-readiness audit.

### Changed

- Public documentation now distinguishes implemented behavior, synthetic
  evidence, unobserved provider assumptions, and owner-gated release steps.
- Package and community metadata prepare the human-approved `0.1.0` Alpha
  release candidate without asserting that publication has occurred.

### Security

- The Workbench serve API digests stable upstream identifiers by default and
  remains loopback-only, GET/HEAD-only, and backed by a SELECT-only database
  role.

[Unreleased]: https://github.com/PranavMishra28/irrevon/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/PranavMishra28/irrevon/releases/tag/v0.1.0
