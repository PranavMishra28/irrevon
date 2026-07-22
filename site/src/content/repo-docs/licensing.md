---
title: "Licensing status"
description: "Why the repository currently carries no license and accepts no contributions, and what closes that decision."
sourcePath: "LICENSING.md"
sourceSha256: "766148e8f44dd934cec7e568c07a09d252b639481b61ac5f72b79b4f80eff4dd"
syncedAt: "2026-07-22"
section: "Governance"
renderTitle: false
---

# Licensing

**Copyright (c) 2026 the repository owner. All rights reserved.**

This repository is publicly readable but is **not released software**. It deliberately
contains no LICENSE file: under default copyright law, no one may reproduce, distribute,
or create derivative works from it. A license will be added only when the licensing
decision closes at the public-release gate — granting rights earlier would narrow that
decision before it is made.

- The licensing decision is **OPEN**: see
  [ADR-0014](docs/decisions/0014-licensing.md) for the options analysis, one-way doors,
  precedents, and current recommendation. It closes at the public-release gate
  ([docs/execution-plan.md](docs/execution-plan.md)), not before.
- **No contributions are accepted** while the decision is open. Do not open pull requests
  with code or content; they cannot be merged (there is no inbound-license basis for
  outside work in an unlicensed repository).
- At first release: LICENSE and NOTICE files, a contribution policy, and a named copyright
  holder replace this notice (release-gate deliverables, ADR-0014).
