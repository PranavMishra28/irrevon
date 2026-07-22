---
title: "Adapter development"
description: "What a destination adapter is, why every adapter ships a machine-readable capability declaration, and what exists today (reference destinations only)."
order: 4
claims:
  - capability-declaration
  - tiers-table
  - implemented-first-slice
---

An adapter binds the engine to one destination — a payment API, a booking system, a
reference stub — and must **prove its destination's semantics in writing** before the
engine will trust it with an irreversible dispatch. That proof is the capability
declaration.

## Status, plainly

Only the in-repo **reference destinations** exist today (the flagship demo runs against
`refdest-c2`). Real-sandbox adapters are gated behind milestone M4, and the adapter
Python interface is deliberately not frozen yet — per-effect-type parameter schemas and
the adapter interface schema are deferred with it. What is frozen enough to build
against is the exchange format below.

## The capability declaration

Every adapter ships a version-pinned, cited, machine-readable declaration validated
against [`capability-declaration.schema.json`](/docs/reference/schemas/). It answers,
with citations into the destination's documentation:

| Field group | Question it answers |
|---|---|
| `tier` | C1 (dependable native idempotency), C2 (queryable authoritative status), or C3 (opaque)? |
| idempotency semantics | Does the destination honor a client key? For how long? Scoped to what? |
| queryability + `list_queryable` | Can the destination be asked "does this effect exist?" — and can it be listed over a window (what the orphan sweep needs)? |
| `client_ref_field` | Which request field carries our reference ID that the destination stores and returns? |
| `consistency` bounds | How stale can a read-back be? This calibrates confirmed-absence — recovery never re-dispatches on a read inside the uncertainty window. |

The tier is not a quality grade; it is what the destination exposes, and it determines
what any client-side system can honestly guarantee there: C1 duplicates are prevented
natively (Irrevon expects to add nothing — the pre-committed null), C2 duplicates are
detected by query with safe re-dispatch after confirmed absence, C3 lost and orphaned
effects are undetectable for every method.

## Contract drift is a first-class event

If the destination changes behavior — a key TTL shortens, a list endpoint paginates
differently — the declaration must be updated, the adapter retested, and a deviation
recorded as a decision record. An adapter whose declaration is wrong is worse than no
adapter: the engine calibrates recovery behavior from those fields.

## Writing one (when M4 opens)

The reference destinations in `src/irrevon/adapters/` are the working template: wire
I/O lives only in the adapter module, the declaration is loaded and digest-pinned at
registration time (every record carries the declaration digest that governed it), and
the adapter exposes dispatch, status query, and — where `list_queryable` — windowed
listing for the sweep. Follow the schema's example suite: the `valid-*.json` examples
are executable documentation, and the `invalid-*.json` suite is the rejection contract.
