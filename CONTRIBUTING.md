# Contributing to Irrevon

Irrevon welcomes focused code, documentation, test, adapter, and benchmark
contributions. Contributions are licensed under Apache-2.0 on the same terms as
the repository and require a Developer Certificate of Origin sign-off. There is
no CLA.

## Before you start

1. For a small bug or documentation fix, open a pull request directly.
2. For a new feature, trust-boundary change, schema change, or benchmark-design
   change, open a proposal issue first. These changes may require an ADR.
3. For a vulnerability, do **not** open an issue. Use GitHub's private
   vulnerability reporting flow described in [SECURITY.md](SECURITY.md).
4. For suspected benchmark leakage, oracle contamination, or misleading
   scientific evidence, use the benchmark-integrity issue form unless disclosure
   would expose a vulnerability.

The project is intentionally narrow: C2 reconciliation for irreversible
external effects, a read-only local Workbench, and a falsifiable benchmark. A
contribution that expands that scope needs explicit owner agreement.

## Developer setup

Prerequisites are Git, [uv](https://docs.astral.sh/uv/), Docker with Compose,
Node 24, and Corepack.

```bash
git clone https://github.com/PranavMishra28/irrevon.git
cd irrevon
uv sync --locked
corepack enable
make tools
make check
```

Run the Python unit and integration tests:

```bash
make py-check
make py-test
make py-test-integration
make py-db-down
```

Frontend and site changes have their own gates:

```bash
make web-check web-test web-e2e
make site-check site-build site-test
```

`make check-all` is the complete routine validation ladder. `make launch-audit`
adds release, package, community, privacy, and deployment checks without
publishing anything.

## Sign every commit

Every pull-request commit must certify the
[Developer Certificate of Origin 1.1](DCO).
Use Git's sign-off flag:

```bash
git commit -s -m "concise description"
```

This adds a trailer:

```text
Signed-off-by: Your Name <your-address@example.invalid>
```

Use your own real name and an email address you are entitled to use. GitHub's
privacy-preserving `noreply` address is acceptable. By signing off, you certify
the DCO; it is not a CLA or copyright assignment. If a commit lacks the trailer,
amend it locally and force-push only your own contribution branch.

## Pull-request expectations

- Keep one purpose per PR and explain the behavior and boundary.
- Add or update tests for changed behavior.
- Preserve every existing validation, security, accessibility, and benchmark
  safeguard.
- Do not include credentials, personal data, real customer/provider records,
  production endpoints, private research notes, generated package artifacts, or
  copied proprietary material.
- Label synthetic fixtures and unobserved provider behavior explicitly.
- Update user-facing documentation and `CHANGELOG.md` when behavior changes.
- Run `make check` before every commit and report the other gates you ran.

The state machine in `src/irrevon/statetable.py`, accepted ADRs, frozen
preregistration sections, schemas, and the master document have stricter change
rules. Read [AGENTS.md](AGENTS.md) before touching those surfaces.

## Documentation and adapters

Documentation fixes use the same pull-request and DCO path. Canonical repository
documents mirrored into the website must be regenerated with the site sync
command documented in [site/README.md](site/README.md).

For a new destination, start with the
[adapter-development guide](site/src/content/guides/adapter-development.md).
Provider claims need primary-source citations, a capability declaration,
strict synthetic contract tests, and clear `observed` versus `unobserved`
attribution. Never put a real key in a fixture or run a live provider call as
part of a contribution.

## Review and governance

Maintainers may close work that is unsafe, out of scope, scientifically
misleading, unlicensed, or impossible to maintain. DCO sign-off is required but
does not guarantee acceptance. See [GOVERNANCE.md](GOVERNANCE.md),
[SUPPORT.md](SUPPORT.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
