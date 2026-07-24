# Security policy

## Reporting a vulnerability

If this repository is public **and** GitHub shows Security → "Report a
vulnerability", use that private vulnerability reporting form. It is the only
ratified private reporting channel. If the option is not visible, do not open a
public issue or discussion: no fallback private channel is currently published.

- Acknowledgement target: 7 days. Triage/assessment target: 30 days.
- Solo-maintained project: there is no bug bounty and no SLA; reports are
  prioritized by severity and exploitability.
- Scope: this repository — engine (`src/irrevon/`), migrations, workbench (`web/`),
  site (`site/`), CI workflows. Benchmark-integrity issues (oracle manipulation,
  fixture leakage, holdout exposure) are IN scope and treated as Sev-1.
- Out of scope: vulnerabilities in third-party dependencies without an
  Irrevon-specific exploit path (report upstream); the deliberately-unreleased
  status of the package.
- The static marketing site is publicly hosted under ADR-0027. It does not run the
  Irrevon engine or expose an Irrevon API, workbench, or production ledger, and it is
  not an authorized penetration-testing target. No hosted product service or live
  engine target currently exists. Do not test against anyone's production
  infrastructure.
- Include reproduction steps; never include real credentials (sandbox-only keys are
  still treated as secrets here — see
  [docs/security-policy.md](docs/security-policy.md)).
- Safe harbor: good-faith research within this scope will not be met with legal
  action by the maintainer. *(This wording has not been reviewed by counsel.)*
- Coordinated disclosure: proposed embargo 90 days or until a fix ships, whichever
  is sooner; credit given unless you decline.

The development-process threat model (agent execution policy, containment layers)
is a separate document: [docs/security-policy.md](docs/security-policy.md) — linked,
not duplicated.
