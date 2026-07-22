# Contributing to Irrevon

**Short version: not yet.** This repository is publicly readable but unlicensed
(see [LICENSING.md](LICENSING.md)) while the licensing decision
([ADR-0014](docs/decisions/0014-licensing.md)) is open. Until it closes:

- **Pull requests with code or content cannot be merged.** There is no license
  granting you rights to contribute derivative work, and no inbound-license basis
  for us to accept it. PRs will be closed with a pointer to this file.
- **Issues are welcome** for defect reports and questions. By filing an issue you
  agree its text may inform the project. Do not paste code you consider yours.
- **Security reports** go through private vulnerability reporting — see
  [SECURITY.md](SECURITY.md). Do not open public issues for suspected
  vulnerabilities.

## What will change when the licensing decision closes

The plan of record (ADR-0014, subject to change until ratified):

1. LICENSE/NOTICE files land and this document is replaced with a real guide.
2. Inbound = outbound, under a **Developer Certificate of Origin** (DCO):
   every commit Signed-off-by, enforced by a required status check.
3. Depending on the chosen license posture, contributions to the reference engine
   may be additionally gated (engine-scoped CLA or maintainer-only) to preserve
   licensing optionality; harness/schemas/web contributions will be DCO-only.
4. No general CLA is planned.

Until then, the most useful contributions are: running the demo and filing
precise defect reports, and citing the benchmark preregistration in review.
