# Project status

Irrevon is a public Apache-2.0 research preview. The source, deterministic
synthetic demo, single-writer engine and worker, local read-only Workbench,
benchmark development harness, and package build are implemented. Contributions
are open under inbound-equals-outbound Apache-2.0 with mandatory DCO 1.1
sign-off and no CLA.

No package or release has been published. The preregistration remains an
unfrozen draft, no confirmatory results exist, and no independent reproduction
is claimed. Stripe C1 and EasyPost C2 adapters are test/sandbox-key-gated drafts
that have never been live-called.

The evaluated deployment boundary is self-hosted, PostgreSQL 17, and at most
one active writer. It is **not yet a supported production topology**: the
standalone worker does not own a durable registration/dispatch ingress, and
fresh-cluster restore and catch-up behavior remain incomplete. The Workbench is
a loopback-only read surface. Multi-writer operation, a hosted control plane,
qualified live-provider behavior, production readiness, scientific validation,
and production battle-testing are not claimed.

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
