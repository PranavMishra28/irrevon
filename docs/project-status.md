# Project status

Irrevon is a public Apache-2.0 `v0.1.0` Alpha candidate. The source,
deterministic synthetic demo, single-writer engine and worker, local read-only
Workbench, benchmark development harness, and distribution pipeline are
implemented. Contributions are open under inbound-equals-outbound Apache-2.0
with mandatory DCO 1.1 sign-off and no CLA.

The release-state source remains `candidate` until PyPI and GitHub provide
verifiable publication evidence. The preregistration remains an unfrozen draft,
no confirmatory results exist, and no independent reproduction is claimed.
Stripe C1 and EasyPost C2 adapters are test/sandbox-key-gated drafts that have
never been live-called.

The evaluated deployment boundary is self-hosted, PostgreSQL 17, and at most
one active writer. It is **not yet a supported production topology**: the
standalone worker does not own a durable registration/dispatch ingress, and
fresh-cluster restore and catch-up behavior remain incomplete. The Workbench is
a loopback-only read surface. Multi-writer operation, a hosted control plane,
qualified live-provider behavior, production readiness, scientific validation,
and production battle-testing are not claimed.

## Public launch read-back

The configured public alias, <https://irrevon.vercel.app/>, is a ready
main-only Git deployment. Its `/version.json` reports the exact current `main`
commit and the `production` environment. The launch process repeats that
read-back after each merge.

Public issue forms are ready for bugs, documentation, benchmark-integrity
reports, and scoped proposals. GitHub Discussions and all six default
categories are enabled and publicly linked; the exact welcome post is created
after this candidate reaches `main`. Private vulnerability reporting is
enabled and remains the only vulnerability channel.

The 2026-07-24 owner-settings read-back found an active default-branch ruleset
with no bypass actors, immutable releases, selected Actions allowlisting,
platform SHA-pin enforcement, and a protected `release` environment.
Non-provider secret scanning remains unavailable; the unrelated `sandbox` and
`benchmark` environments remain absent.

## Public-history privacy boundary

Secret scanning is clean, but the repository does not claim that public history
is PII-free. Known pre-redaction personal prose and a pre-scrub environment
record remain reachable in history. The owner must explicitly accept that
exposure or coordinate a history rewrite and complete ref replacement; agents
must not rewrite public history. No sensitive historical value is reproduced
in launch documentation.

## Owner governance checklist

Implementation has landed for seven decisions that remain explicitly
**proposed**, not accepted: ADR-0020, ADR-0021, ADR-0022, and ADR-0030 through
ADR-0034. Before a release, the owner must review each decision against the
implementation and either ratify it through the repository's human-only ADR
process, request changes, or leave it proposed with the limitation disclosed.
Repository automation and this status page never convert implementation into
ratification.

This readable summary corresponds to
[project-status.json](project-status.json). Run `make public-truth` to verify
the primary launch surfaces, or read the complete
[release roadmap](execution-plan.md).
