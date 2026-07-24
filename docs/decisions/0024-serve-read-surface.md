---
id: ADR-0024
title: "`irrevon serve` — the loopback read-only workbench surface"
status: accepted (owner serve directive, 2026-07-21); decision item 5 superseded by ADR-0036
date: 2026-07-21
supersedes: —
---

## Context

The workbench (`web/`, ADR-0016) shipped fixture-backed because no read server existed
(review-queue BI-4). The owner's rebuild directive of 2026-07-21 ordered the serve
workstream: a local read surface so the packaged CLI can serve the workbench over real
ledger data. Constraints: ADR-0013's thin-stack discipline (no new runtime deps without
cause), the read-only-in-depth posture (master doc §9: the browser can never mutate), and
ADR-0018's single-wheel distribution (the CLI ships the built web assets and serves them
Node-free). Proposed by the BE builder from the serve design spec; implementation lives in
`src/irrevon/serve.py` + `src/irrevon/api/readviews.py` with migration
`0005_read_role.sql` and the `tests/serve/` suite.

## Decision

1. **stdlib `http.server` (`ThreadingHTTPServer`), zero new runtime deps.** FastAPI/Flask
   rejected: no request bodies, one local user, thin-stack discipline (ADR-0013).
2. **Loopback-only:** hard-coded 127.0.0.1 bind; no `--host` flag and no env override
   exists; a post-bind assertion refuses non-loopback (tested by monkeypatching the bind
   constant).
3. **Read-only in depth, three layers:** GET/HEAD-only handler (405 otherwise; row-count
   proof test) → `irrevon_read` SELECT-only role (migration 0005; no EXECUTE on the locked
   ledger functions; grants audit test) → `default_transaction_read_only=on` per session
   AND at role level.
4. **Q1 lean-item deviation from RFC-002 §9:** the served list item is
   `{record, classification, finding}` (the shipped workbench shape); the full composition
   lives on the inspect route. Adding fields later is additive, never breaking.
5. **stable_ids served unredacted on this surface** — loopback single-user trust domain;
   redaction stays a CLI-inspect affordance (`--reveal`). Flagged for explicit
   ratification (review-queue §3).
6. **Additive error codes:** `query_invalid`, `method_not_allowed`, `internal` join the
   established API error set (MINOR events).
7. **Version handshake:** `/api/v1` namespace + payload `schema_version` +
   `Irrevon-Schema-Version: 1` response header on every API response including errors;
   the workbench refuses to render on a mismatch (full-surface refusal, never partial).
8. Entry point remains `irrevon.cli:entrypoint` (ADR-0018's text says `main`; noted here,
   not churned).

## Alternatives

- **FastAPI/Flask/Starlette** — rejected: dependency weight and attack surface for a
  loopback GET-only surface with one user.
- **Serving the workbench from Vite/Node** — rejected: ADR-0018 requires strangers never
  to need Node; the wheel embeds `web/dist` and the CLI serves it statically.
- **Reusing `irrevon_app` for reads** — rejected: the app role holds EXECUTE on the locked
  transition functions; the read surface must be unable to mutate even if the handler is
  wrong (defense in depth).

## Consequences

- The workbench live mode (`web/` `useLiveStatus`, LIVE chip, disconnected banner,
  version refusal) has a real backend; the joint E2E (`make serve-live` + the Playwright
  live suite) proves the integration against the real engine.
- Migration 0005 becomes part of the baseline schema; `irrevon doctor` gains a
  `serve_ready` check.
- Enforced by: `tests/serve/` (loopback refusal, method rejection, privilege audit,
  version handshake, route conformance, inspect byte-parity, traversal/SPA-fallback,
  zero-outbound), and the workbench live-boundary suite.

## Risks

- A future route added outside `api/readviews.py` could bypass the single-producer
  discipline — mitigated by route-conformance tests and review.
- stable_ids exposure ruling (Decision 5) could be reversed by the owner — the change
  would be a redaction layer on the serve views, additive.

## Reopen trigger

A multi-user or non-loopback deployment need arises (forces the auth/bind questions this
ADR explicitly excludes); or the owner rejects the stable_ids exposure ruling in the
review queue; or RFC-002 §9's full Q1 composition becomes required by a consumer.
