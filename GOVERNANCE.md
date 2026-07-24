# Governance

Irrevon is an owner-led open-source project. The repository owner is the
maintainer of record and has final responsibility for scope, releases, security
coordination, benchmark integrity, and project governance.

## How decisions are made

- Defect fixes, tests, and documentation improvements use normal pull-request
  review.
- Material feature proposals begin as GitHub issues.
- Changes to invariants, trust boundaries, schemas, guarantees, benchmark
  design, or security controls require an ADR before merge.
- Accepted ADRs are append-only and are superseded rather than rewritten.
- Frozen preregistration content can change only through its amendment process.
- Releases, preregistration freezes, live-provider observations, deployment,
  repository settings, and external legal actions require an explicit human
  decision.

Discussion aims for evidence-backed consensus, but the maintainer decides when
consensus is absent. Decisions may be revisited using the reopen trigger in the
relevant ADR.

## Roles

The project currently has one role: **maintainer**. Maintainers review and merge
changes, triage issues, coordinate vulnerabilities, cut releases, and enforce
the Code of Conduct. Contributors acquire no special authority merely by making
a contribution.

Additional maintainers may be added after a sustained record of technically
sound, security-conscious, and constructive participation. Changes are recorded
in [MAINTAINERS.md](MAINTAINERS.md); no nomination timetable is promised.

## Contributions and licensing

Contributions use inbound-equals-outbound Apache-2.0 and require DCO 1.1
sign-off on every commit. There is no CLA. See
[CONTRIBUTING.md](CONTRIBUTING.md) and
[ADR-0035](docs/decisions/0035-external-contributions.md).

## Conduct, security, and conflicts

Community behavior is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Vulnerabilities use the private path in [SECURITY.md](SECURITY.md). Other
conflicts of interest should be disclosed in the pull request or issue; the
maintainer may seek independent review or recuse when another maintainer exists.
