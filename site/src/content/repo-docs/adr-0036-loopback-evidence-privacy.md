---
title: "Loopback evidence privacy digests stable identifier values by default"
sourcePath: "docs/decisions/0036-loopback-evidence-privacy.md"
sourceSha256: "6d0b94a1a0b327f5298d91f29e5bd5824752aa8936afc1e838a73cb8a5ae72df"
syncedAt: "2026-07-24"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0036"
  status: "accepted"
  date: "2026-07-23"
  supersedes: "ADR-0024 decision item 5"
---

## Context

ADR-0024 made `irrevon serve` loopback-only, GET/HEAD-only, and database
read-only, but returned upstream `stable_ids` values verbatim. The CLI redacted
those same values unless an operator explicitly supplied `--reveal`. Loopback
reduces network exposure; it does not guarantee that browser screenshots,
extensions, exported diagnostics, screen sharing, or local logs remain private.
The two surfaces therefore had contradictory safe defaults.

## Decision

`irrevon serve` MUST retain stable-identifier field names but replace every
value with a deterministic SHA-256 digest representation. The effect ID,
operation ID, finding ID, and other Irrevon-minted opaque identifiers remain
available because they are necessary for evidence navigation and do not reveal
the upstream value from which identity was derived.

No HTTP reveal parameter or route exists. An operator may reveal upstream
stable-identifier values only through the local CLI's explicit `irrevon inspect
--reveal` option. Request paths may be logged; query strings, request bodies,
stable-identifier values, credentials, and DSNs may not. Fixtures and public
screenshots use synthetic values but should still model the digested serve
contract.

## Alternatives

- **Trust every loopback browser:** rejected; local software, screenshots, and
  screen sharing can cross that boundary.
- **Return a constant redaction marker:** rejected because deterministic
  digests preserve equality investigation without exposing raw values.
- **Add a browser reveal toggle:** rejected because it would make the read
  surface a raw-data export mechanism and require an authentication design.
- **Remove identifier keys:** rejected because keys explain identity
  construction and do not contain the upstream value.

## Consequences

Workbench evidence can compare digested values but cannot display the original
upstream identifier. Local operators needing the value use the CLI explicitly.
Regression tests lock the digest format, absence of raw values, generic storage
errors, and byte parity with default (non-reveal) CLI inspection.

## Risks

Unsalted digests of low-entropy identifiers may be guessable. They are an
exposure reduction, not anonymization. Operators should keep the Workbench
loopback-only, avoid untrusted browser extensions, and treat evidence exports as
sensitive.

## Reopen trigger

Revisit if the Workbench gains authentication and a separately threat-modeled
reveal capability, or if an operator study shows that keyed deployment-local
digests are required and their key lifecycle can be supported safely.
