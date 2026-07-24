---
title: "External contributions use Apache-2.0 inbound=outbound with mandatory DCO"
sourcePath: "docs/decisions/0035-external-contributions.md"
sourceSha256: "802be8b389dfa8233f95a03c67ff34c493ae9bd11b1feea3ff6cf9f6dc130c5e"
syncedAt: "2026-07-24"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0035"
  status: "accepted"
  date: "2026-07-23"
  supersedes: "ADR-0014 contributor-governance half"
---

## Context

ADR-0028 established Apache-2.0 as the repository's outbound license. ADR-0014
left the inbound contribution mechanism open, so maintainers could not accept
outside code or documentation. The owner explicitly opened contributions in the
2026-07-23 launch directive and selected inbound-equals-outbound Apache-2.0,
Developer Certificate of Origin 1.1 sign-off on every contributed commit, and no
Contributor License Agreement.

## Decision

Irrevon accepts code, documentation, tests, benchmark engineering, and other
repository contributions through ordinary GitHub pull requests. Contributions
are provided under the same Apache-2.0 terms that govern the repository. Every
contributed commit MUST contain a `Signed-off-by:` trailer certifying the
[Developer Certificate of Origin 1.1](https://developercertificate.org/).
CI enforces the trailer on pull-request commits. Irrevon does not require or
offer a CLA.

Security vulnerabilities use GitHub private vulnerability reporting rather than
public issues. Suspected benchmark-integrity problems that do not expose a
vulnerability use the dedicated public issue form. Maintainer judgment, tests,
scope, scientific integrity, and the Code of Conduct remain merge conditions;
DCO sign-off is necessary but not sufficient.

## Alternatives

- **CLA:** rejected by owner directive; unnecessary for inbound=outbound
  Apache-2.0 and adds contributor friction.
- **Copyright assignment:** rejected; broader than necessary and inconsistent
  with the selected community posture.
- **No outside contributions:** superseded by the owner launch directive.
- **DCO app as the sole control:** rejected; the repository carries a
  deterministic CI check so enforcement is reviewable and locally testable.

## Consequences

- `CONTRIBUTING.md`, community files, templates, and the site may invite pull
  requests.
- `make dco` and the PR workflow enforce sign-off without receiving secrets or
  executing contributor code.
- Contributors retain copyright and grant Apache-2.0 rights; accepted commits
  remain under Apache-2.0.
- The first accepted outside contribution does not create a relicensing grant
  beyond Apache-2.0. Any future incompatible relicensing may require contributor
  consent or removal/rewrite of their contributions.

## Risks

A sign-off is a contributor certification, not identity verification or a
warranty that a contribution is safe. Maintainers still review provenance,
security, licensing, scope, and benchmark integrity.

## Reopen trigger

Revisit if DCO 1.1 is superseded, the repository changes license, a demonstrated
abuse defeats commit-range enforcement, or counsel identifies a material defect
in this inbound=outbound posture.
