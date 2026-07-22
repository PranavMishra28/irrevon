# Security policy

## Reporting a vulnerability

Use **GitHub private vulnerability reporting** (Security tab → "Report a
vulnerability") on this repository. It is enabled and is the only supported channel.
Please do NOT open a public issue or discussion for suspected vulnerabilities.

- Acknowledgement target: 7 days. Triage/assessment target: 30 days.
- Solo-maintained project: there is no bug bounty and no SLA; reports are
  prioritized by severity and exploitability.
- Scope: this repository — engine (`src/irrevon/`), migrations, workbench (`web/`),
  site (`site/`), CI workflows. Benchmark-integrity issues (oracle manipulation,
  fixture leakage, holdout exposure) are IN scope and treated as Sev-1.
- Out of scope: vulnerabilities in third-party dependencies without an
  Irrevon-specific exploit path (report upstream); the deliberately-unreleased
  status of the package.
- No production systems or hosted services exist; there is no live target. Do not
  test against anyone's production infrastructure.
- Include reproduction steps; never include real credentials (sandbox-only keys are
  still treated as secrets here — see
  [docs/security-policy.md](docs/security-policy.md)).
- Safe harbor: good-faith research within this scope will not be met with legal
  action by the maintainer. *(Wording to be counsel-confirmed at license adoption.)*
- Coordinated disclosure: proposed embargo 90 days or until a fix ships, whichever
  is sooner; credit given unless you decline.

The development-process threat model (agent execution policy, containment layers)
is a separate document: [docs/security-policy.md](docs/security-policy.md) — linked,
not duplicated.
