"""Conventional baseline arms B0–B6 + the preselected composite (master doc §8.3).

Baselines are NEVER weakened (benchmark-integrity rule): each arm implements
its strategy's honest, strongest form, and B5 reuses the SAME
``B5DurableRuntime`` operationalization as the flagship demo's contrast leg —
one B5, not a bench-weakened or demo-weakened one (api/baselines.py).

B7 (model-assisted semantic matching) is registered but NOT operationalized:
it requires a model with budget parity to R's advisory classifier — a Stage-B
operationalization item. The registry refuses to run it rather than shipping a
strawman.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from irrevon.adapters.base import Adapter, DispatchOrder, DispatchResult
from irrevon.api.baselines import B5DurableRuntime
from irrevon.bench.arms import ArmDriver, ArmSpec, Episode, TrialReport
from irrevon.identity import canonical_digest

__all__ = ["CONVENTIONAL_SPECS", "ConventionalArm", "make_conventional_driver"]

_DISPATCH_DEADLINE_S = 10.0


class ConventionalArm(ArmDriver):
    """One parameterized driver covers the conventional ladder; the feature
    flags ARE the arm definitions and are captured in each spec's config
    (config digests land in the run manifest)."""

    def __init__(
        self,
        spec: ArmSpec,
        adapter: Adapter,
        workdir: Path,
        *,
        stable_ref: bool,
        agent_key: bool,
        arg_hash_dedup: bool,
        status_check: bool,
        durable_journal: bool,
    ) -> None:
        self.spec = spec
        self._adapter = adapter
        self._workdir = workdir
        self._stable_ref = stable_ref
        self._agent_key = agent_key
        self._arg_hash_dedup = arg_hash_dedup
        self._status_check = status_check
        self._durable_journal = durable_journal
        self._unit_seed = 0
        self._attempt_counter = 0
        self._dedup_cache: set[str] = set()
        self._runtime: B5DurableRuntime | None = None
        self._journal_path: Path | None = None

    # ── unit lifecycle ─────────────────────────────────────────────────────────

    def begin_unit(self, unit_seed: int) -> None:
        self._unit_seed = unit_seed
        self._attempt_counter = 0
        self._dedup_cache = set()
        if self._durable_journal:
            slug = self.spec.arm_id.lower().replace("+", "-")
            journal = self._workdir / f"{slug}-journal-{unit_seed}.json"
            if journal.exists():
                journal.unlink()
            self._journal_path = journal
            self._runtime = B5DurableRuntime(journal, self._adapter)

    def end_unit(self) -> None:
        self._runtime = None

    # ── client-reference policy (the ladder's identity story) ─────────────────

    def _client_ref(self, episode: Episode, synthesis: int) -> str:
        if self._stable_ref:
            # Stable workflow-issued operation id: survives retries, crashes,
            # and re-synthesis (B3+). The C2 destination accepts it but does
            # not honor it as an idempotency key — the wedge under test.
            return f"wf-{self._unit_seed}-t{episode.trial_index}-0"
        if self._agent_key:
            # Agent-generated key: stable within one synthesis; the model
            # REGENERATES it on re-synthesis and after process death (B2's
            # documented residual failure mode).
            return f"agent-{self._unit_seed}-t{episode.trial_index}-syn{synthesis}"
        # No identity story (B0/B1): every wire attempt is a fresh reference.
        self._attempt_counter += 1
        return f"anon-{self._unit_seed}-t{episode.trial_index}-n{self._attempt_counter}"

    # ── wire primitives ────────────────────────────────────────────────────────

    def _send(
        self, episode: Episode, payload: dict[str, Any], synthesis: int, log: list[dict[str, Any]]
    ) -> DispatchResult | None:
        """One attempt; returns None when arg-hash dedup suppresses the send."""
        if self._arg_hash_dedup:
            digest = canonical_digest(payload)
            if digest in self._dedup_cache:
                log.append({"action": "suppressed", "reason": "arg-hash-dedup"})
                return None
            self._dedup_cache.add(digest)
        ref = self._client_ref(episode, synthesis)
        if self._runtime is not None:
            outcome = self._runtime.execute(ref, episode.effect_type, payload)
            log.append({"action": "dispatch", "client_ref": ref, **outcome})
            return DispatchResult(
                transport_outcome=outcome["transport_outcome"],
                destination_ref=outcome["destination_ref"],
            )
        result = self._adapter.dispatch(
            DispatchOrder(
                operation_id=ref,
                effect_type=episode.effect_type,
                payload=payload,
                client_ref=ref,
            ),
            _DISPATCH_DEADLINE_S,
        )
        log.append(
            {
                "action": "dispatch",
                "client_ref": ref,
                "transport_outcome": result.transport_outcome,
            }
        )
        return result

    def _status_present(self, episode: Episode, log: list[dict[str, Any]]) -> str:
        """B6 provider-native status check by the stable reference.

        Where the destination exposes no query (C3), the check is honestly
        UNAVAILABLE — the arm degrades to its remaining legs (B6→B3 retry,
        composite→B5 journal retry), which is exactly the master doc §8.3
        residual: "not general; varies by provider"."""
        from irrevon.errors import CapabilityUnsupported

        try:
            answer = self._adapter.status_query(
                client_ref=self._client_ref(episode, 0), deadline_s=_DISPATCH_DEADLINE_S
            )
        except CapabilityUnsupported:
            log.append({"action": "status-check", "result": "UNAVAILABLE"})
            return "UNAVAILABLE"
        log.append({"action": "status-check", "result": answer.result})
        return answer.result

    # ── the episode ────────────────────────────────────────────────────────────

    def run_episode(self, episode: Episode) -> TrialReport:
        log: list[dict[str, Any]] = []
        report = TrialReport(
            trial_index=episode.trial_index,
            arm_outcome="unresolved-unknown",
            dispatch_attempted=False,
            detail={"log": log, "authority_concept": False, "branch_concept": False},
        )
        # No authority/branch model on the conventional ladder: the stale/
        # cancelled conditions are invisible; dispatch proceeds (§2.1 L4/L5 —
        # the block/allow column is N/A-by-arm; effect outcomes still score).
        payload = dict(episode.parameters)
        synthesis = 0

        result = self._send(episode, payload, synthesis, log)
        report.dispatch_attempted = True
        if result is None:  # cannot happen on the first send; defensive
            report.arm_outcome = "suppressed"
            return report

        if result.transport_outcome == "OK":
            report.arm_outcome = "committed"
            return report
        if result.transport_outcome == "FAILED":
            report.arm_outcome = "failed"
            return report

        # Ambiguous transport outcome (TIMEOUT/LOST). Enact the client-side
        # fault script: crash, storm, or plain retry — per the arm's strategy.
        if episode.fault == "crash-after-effect-before-response":
            self._crash(log)
            synthesis += 1  # an agent re-synthesizes after restart
            if self._runtime is not None:
                return self._recover_durable(episode, report, log)
            retry_payload = payload
        elif episode.fault == "semantic-resynthesis" and episode.resynth_parameters is not None:
            synthesis += 1
            retry_payload = dict(episode.resynth_parameters)
        else:
            retry_payload = payload

        budget = max(1, episode.retries)
        for _ in range(budget):
            if self._status_check:
                answer = self._status_present(episode, log)
                if answer == "PRESENT":
                    report.arm_outcome = "committed"
                    report.detail["detected_by"] = "status-check"
                    return report
                if answer == "INDETERMINATE":
                    report.arm_outcome = "ambiguous-unresolved"
                    return report
                # ABSENT ⇒ safe to retry; UNAVAILABLE (no query on this
                # destination) ⇒ the check leg is inoperative — fall through
                # to the underlying retry strategy.
            retry = self._send(episode, retry_payload, synthesis, log)
            if retry is None:
                # Arg-hash dedup swallowed the retry: the arm now BELIEVES
                # nothing more can be done and cannot distinguish done from
                # lost — B1's honest residue.
                report.arm_outcome = "unresolved-unknown"
                return report
            if retry.transport_outcome == "OK":
                report.arm_outcome = "committed"
                return report
            if retry.transport_outcome == "FAILED":
                report.arm_outcome = "failed"
                return report
        report.arm_outcome = (
            "ambiguous-unresolved" if self._status_check else "unresolved-unknown"
        )
        return report

    # ── crash + recovery semantics ────────────────────────────────────────────

    def _crash(self, log: list[dict[str, Any]]) -> None:
        """Process death: all in-memory state is lost. The durable journal (a
        file) survives; the arg-hash cache and agent keys do not."""
        self._dedup_cache = set()
        if self._runtime is not None and self._journal_path is not None:
            self._runtime = B5DurableRuntime(self._journal_path, self._adapter)
        log.append({"action": "crash", "lost": ["dedup-cache", "agent-keys"]})

    def _recover_durable(
        self, episode: Episode, report: TrialReport, log: list[dict[str, Any]]
    ) -> TrialReport:
        """Durable-execution restart semantics: retry every op without a
        recorded outcome — same op id, same key (B5). The composite checks the
        destination first (B6 leg) before re-executing."""
        assert self._runtime is not None
        if self._status_check:
            answer = self._status_present(episode, log)
            if answer == "PRESENT":
                report.arm_outcome = "committed"
                report.detail["detected_by"] = "status-check-on-recovery"
                return report
            # ABSENT/UNAVAILABLE/INDETERMINATE: recovery proceeds with the
            # durable-journal retry (the B5 leg of the composite).
        retried = self._runtime.recover()
        log.append({"action": "recover", "retried": [r["op_id"] for r in retried]})
        outcomes = {r["op_id"]: r["transport_outcome"] for r in retried}
        if all(v in ("OK", "FAILED") for v in outcomes.values()) and outcomes:
            report.arm_outcome = (
                "committed" if "OK" in outcomes.values() else "failed"
            )
        elif not outcomes:
            report.arm_outcome = "committed"  # journal says settled pre-crash
        else:
            report.arm_outcome = "unresolved-unknown"
        return report


# ── The ladder registry (specs are data; drivers are built from them) ─────────

_LADDER: dict[str, dict[str, Any]] = {
    "B0": {
        "description": "No protection: fresh request per attempt, no keys, no refs.",
        "retry_behavior": "naive identical retry on ambiguous outcome",
        "flags": {},
        "deviations": (),
    },
    "B1": {
        "description": "Model-argument hashing: local dedup cache over canonical argument digests.",
        "retry_behavior": "identical retry suppressed by arg-hash; re-synthesized retry passes",
        "flags": {"arg_hash_dedup": True},
        "deviations": (),
    },
    "B2": {
        "description": (
            "Agent-generated idempotency keys: stable within one synthesis, "
            "regenerated on re-synthesis/restart."
        ),
        "retry_behavior": (
            "identical retry reuses the key; re-synthesis and restarts mint a new key"
        ),
        "flags": {"agent_key": True},
        "deviations": (),
    },
    "B3": {
        "description": (
            "Stable workflow-issued operation IDs sent as client reference and "
            "idempotency key."
        ),
        "retry_behavior": "identical retry with the same stable key",
        "flags": {"stable_ref": True},
        "deviations": (),
    },
    "B4": {
        "description": (
            "Destination-native idempotency: stable caller key relied on for "
            "destination-side replay."
        ),
        "retry_behavior": (
            "identical retry with the same stable key (destination dedups on C1 only)"
        ),
        "flags": {"stable_ref": True},
        "deviations": (
            "mechanically identical to B3 against refdest (the tier of the destination, "
            "not the caller, decides whether the key is honored); kept as a distinct "
            "ladder entry so C1 cells report it separately",
        ),
    },
    "B5": {
        "description": (
            "Durable runtime + stable op-IDs + native idempotency keys "
            "(strongest conventional single arm)."
        ),
        "retry_behavior": (
            "durable journal; ops without a recorded outcome are retried with "
            "the SAME op-id/key on restart and on ambiguity"
        ),
        "flags": {"stable_ref": True, "durable_journal": True},
        "deviations": (
            "in-process file-journal operationalization shared verbatim with the flagship "
            "demo contrast leg (api/baselines.py) — one B5 for demo and bench by design",
        ),
    },
    "B6": {
        "description": "Provider-native status check: query by stable reference before any retry.",
        "retry_behavior": "status-check-before-retry; retries only on authoritative ABSENT",
        "flags": {"stable_ref": True, "status_check": True},
        "deviations": (),
    },
    "B5+B3+B6": {
        "description": (
            "Preselected composite comparator (AM-7): durable journal + stable "
            "op-IDs + status-check-before-retry."
        ),
        "retry_behavior": (
            "durable journal; recovery and retries gated on a destination "
            "status check by stable reference"
        ),
        "flags": {"stable_ref": True, "durable_journal": True, "status_check": True},
        "deviations": (),
    },
}

CONVENTIONAL_SPECS: dict[str, ArmSpec] = {
    arm_id: ArmSpec(
        arm_id=arm_id,
        description=entry["description"],
        version="0.1.0",
        retry_behavior=entry["retry_behavior"],
        operationalized=True,
        # A durable journal or a status check gives the arm a real "outcome
        # unknown" representation; the stateless arms have none.
        ambiguity_concept=bool(
            entry["flags"].get("durable_journal") or entry["flags"].get("status_check")
        ),
        known_deviations=tuple(entry["deviations"]),
        config={"flags": dict(entry["flags"])},
    )
    for arm_id, entry in _LADDER.items()
}

# B7 is registered, honestly unoperationalized (budget-parity model required).
CONVENTIONAL_SPECS["B7"] = ArmSpec(
    arm_id="B7",
    description="Model-assisted semantic matching (advisory duplicate flagging).",
    version="0.0.0",
    retry_behavior="unoperationalized",
    operationalized=False,
    model=None,
    stage_b_note=(
        "Requires a model with budget parity to R's advisory classifier (AM-7); "
        "operationalizing it is a Stage-B item — running a strawman here would "
        "weaken the ladder, so the registry refuses instead."
    ),
)


def make_conventional_driver(arm_id: str, adapter: Adapter, workdir: Path) -> ConventionalArm:
    spec = CONVENTIONAL_SPECS[arm_id]
    if not spec.operationalized:
        raise ValueError(f"arm {arm_id} is not operationalized: {spec.stage_b_note}")
    flags = spec.config["flags"]
    return ConventionalArm(
        spec,
        adapter,
        workdir,
        stable_ref=bool(flags.get("stable_ref")),
        agent_key=bool(flags.get("agent_key")),
        arg_hash_dedup=bool(flags.get("arg_hash_dedup")),
        status_check=bool(flags.get("status_check")),
        durable_journal=bool(flags.get("durable_journal")),
    )
