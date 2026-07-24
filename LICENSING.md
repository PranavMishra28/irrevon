# Licensing

**This repository is licensed under the Apache License, Version 2.0** — see
[LICENSE](LICENSE) (verbatim text) and [NOTICE](NOTICE) (attribution: "Irrevon —
Copyright 2026 Irrevon contributors"). The decision record is
[ADR-0028](docs/decisions/0028-apache-2-license.md), ratified by the owner in writing on
2026-07-21; it resolves the license half of
[ADR-0014](docs/decisions/0014-licensing.md). The license grant applies to every copy of
the covered source that is distributed; repository visibility is an owner-controlled
hosting setting and does not change the license text committed here.

What this does **not** change:

- **Contributions use the same license.** Under
  [ADR-0035](docs/decisions/0035-external-contributions.md), outside code,
  documentation, tests, and benchmark work are accepted through pull requests
  under Apache-2.0, with a Developer Certificate of Origin 1.1 sign-off on every
  commit. No CLA or copyright assignment is required.
- **Distribution lifecycle.** Source checkouts and packaged artifacts carry the
  same Apache-2.0 terms, NOTICE attribution, third-party notices, and Alpha
  maturity classifier. Availability from a package index does not imply
  scientific validation, provider qualification, production adoption, trademark
  clearance, or production readiness.
- **Trademarks.** Apache-2.0 §6 grants no rights to the "Irrevon" name or marks.
  No separate trademark registration or conformance program is claimed.

Third-party material: the direct-dependency inventory lives in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) (drift-gated by `make check`); the
vendored IBM Plex font subsets in `web/` and `site/` remain under the SIL Open Font
License (their OFL.txt travels with them); asset provenance is ledgered in
[ASSETS.md](ASSETS.md) and [site/ASSETS.md](site/ASSETS.md). psycopg
(LGPL-3.0-only) is the single non-permissive runtime dependency — separately installed,
never vendored; the recorded compatibility analysis is in the review queue, with the
documented-exception ruling still owed.
