---
title: "Licensing status"
description: "Apache-2.0 licensing and contribution posture: inbound=outbound, mandatory DCO 1.1 sign-off, no CLA, and the remaining trademark and release gates."
sourcePath: "LICENSING.md"
sourceSha256: "e3240e67a4c58d2635cdf3e2426b32a20a4373ea2f795e6634ada8eb7741c42d"
syncedAt: "2026-07-24"
section: "Governance"
renderTitle: false
---

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
- **Pre-release status.** Nothing is on any package index; packaged releases remain
  gated by the execution-plan public-release gate (clearances, counsel name screen,
  sanitization review, human sign-off). Packaging license metadata (SPDX expression and
  classifier) lands with the ADR-0018 M8 release mechanics.
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
