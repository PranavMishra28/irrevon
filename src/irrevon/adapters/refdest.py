"""Deterministic reference destination — refdest (RFC-002 §8; adapters.md §2/§3).

One codebase, three tier profiles, all deterministic under a seed with a seeded
virtual clock:

- **C2** (the flagship profile): create/status/list/client-ref query, NO native
  idempotency (identical request twice ⇒ two effects — the C2 property under
  test), client-ref uniqueness deliberately unenforced, configurable
  default-filter quirk, seeded fault schedule.
- **C1**: honors idempotency keys within the declared window (cached-response
  replay semantics).
- **C3**: fire-and-forget (202, empty body, no query/list/client-ref); the
  seeded truth log lets the ORACLE see what the system under test cannot — that
  asymmetry is the impossibility demo.

The fault schedule is installed through a control plane the adapter under test
has no code path to (harness-only); faults are a seeded schedule installed
before the run, not live puppeteering. ``destination_ref`` derivation is
collision-resistant: SHA-256 over seed ‖ counter.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from irrevon.adapters.base import Adapter, DispatchOrder, DispatchResult, StatusAnswer
from irrevon.errors import CapabilityUnsupported
from irrevon.identity import canonical_digest

__all__ = ["RefDest", "RefdestAdapter", "WireDropped"]

_EPOCH = datetime(2026, 7, 21, 0, 0, 0, tzinfo=UTC)

FAULT_KINDS = (
    "DROP_RESPONSE_AFTER_COMMIT",
    "DROP_RESPONSE_BEFORE_COMMIT",
    "DELAY",
    "ERROR_5XX_AFTER_COMMIT",
    "ERROR_5XX_NO_COMMIT",
    "DUPLICATE_ACCEPT",
    "THROTTLE_429",
)


class WireDropped(Exception):
    """Connection closed before response bytes (fault-injected)."""

    def __init__(self, committed: bool) -> None:
        super().__init__("connection dropped before response")
        self.committed = committed


@dataclass
class _Fault:
    fault: str
    match: dict[str, Any]
    param: dict[str, Any] = field(default_factory=dict)
    once: bool = True
    consumed: bool = False


class RefDest:
    """The destination itself: in-process store + wire-semantics surface.

    Everything below ``# ── control plane`` is harness-only; the adapter under
    test can only reach the effect API methods.
    """

    def __init__(self, seed: int = 42, profile: str = "C2",
                 default_filter_quirk: bool = False,
                 enrichment_quirk: bool = False) -> None:
        if profile not in ("C1", "C2", "C3"):
            raise ValueError(f"unknown refdest profile {profile!r}")
        self.profile = profile
        self.default_filter_quirk = default_filter_quirk
        # Enrichment quirk: the destination normalizes/enriches the stored
        # representation (server-assigned fields, canonicalized keys) the way
        # real APIs do, so the STORED payload digest no longer equals the
        # digest of the dispatched payload. Oracles that attribute effects by
        # dispatched-payload digest alone break under this quirk by design —
        # it exists to keep them honest (bench oracle hardening).
        self.enrichment_quirk = enrichment_quirk
        self._seed = seed
        self._effects: list[dict[str, Any]] = []
        self._request_log: list[dict[str, Any]] = []
        self._schedule: list[_Fault] = []
        self._request_count = 0
        self._effect_counter = 0

    # ── internals ─────────────────────────────────────────────────────────────

    def _now(self) -> str:
        # Seeded virtual clock: time is part of the determinism contract (C1 N1).
        return (
            (_EPOCH + timedelta(seconds=self._request_count))
            .isoformat()
            .replace("+00:00", "Z")
        )

    def _mint_ref(self) -> str:
        self._effect_counter += 1
        digest = hashlib.sha256(
            f"{self._seed}:{self._effect_counter}".encode()
        ).hexdigest()
        return f"dest_{digest[:32]}"

    def _log(self, op: str, **details: Any) -> None:
        self._request_count += 1
        self._request_log.append(
            {"seq": self._request_count, "op": op, "at": self._now(), **details}
        )

    def _active_fault(
        self, op: str, client_ref: str | None, effect_type: str | None
    ) -> _Fault | None:
        for entry in self._schedule:
            if entry.consumed:
                continue
            m = entry.match
            if "op" in m and m["op"] != op:
                continue
            if "nth_request" in m and m["nth_request"] != self._request_count:
                continue
            if "client_ref" in m and m["client_ref"] != client_ref:
                continue
            if "effect_type" in m and m["effect_type"] != effect_type:
                continue
            if not m:
                continue
            if entry.once:
                entry.consumed = True
            return entry
        return None

    def _insert_effect(
        self,
        effect_type: str,
        payload: dict[str, Any],
        client_ref: str | None,
        idempotency_key: str | None,
        visible_by_default: bool = True,
        via: str = "api",
    ) -> dict[str, Any]:
        stored_payload: dict[str, Any] = dict(payload)
        if self.enrichment_quirk:
            # Server-side normalization/enrichment: the stored object is NOT
            # byte-identical to the dispatched one (real-API behavior).
            stored_payload = {
                "normalized": True,
                "server_fields": {"region": "dev-1", "revision": self._effect_counter + 1},
                "data": stored_payload,
            }
        effect = {
            "destination_ref": self._mint_ref(),
            "effect_type": effect_type,
            # Digest of the STORED representation — under the enrichment
            # quirk this deliberately differs from the dispatched payload's
            # digest (what a read-back-only observer could recompute).
            "payload_digest": canonical_digest(stored_payload),
            # Ground-truth stored payload: control-plane/truth-API only;
            # never exposed through the public effect API (_public).
            "payload": stored_payload,
            "client_ref": client_ref,
            "idempotency_key": idempotency_key,
            "created_at": self._now(),
            # The destination's authoritative total order (request-log seq at
            # creation time) — the history checker's cross-actor anchor.
            "request_seq": self._request_count,
            "status": "created",
            "visible_by_default": visible_by_default,
            "via": via,
        }
        self._effects.append(effect)
        return effect

    @staticmethod
    def _public(effect: dict[str, Any]) -> dict[str, Any]:
        return {
            k: effect[k]
            for k in ("destination_ref", "effect_type", "client_ref", "created_at",
                      "status")
        }

    # ── effect API (what the adapter under test sees) ─────────────────────────

    def api_create(
        self,
        effect_type: str,
        payload: dict[str, Any],
        client_ref: str | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[int, dict[str, Any], int]:
        """Returns (status, body, delay_ms); raises WireDropped on drop faults."""
        if self.profile == "C3":
            raise CapabilityUnsupported("C3 profile has no create/effects API")
        self._log("create", client_ref=client_ref, effect_type=effect_type)
        fault = self._active_fault("create", client_ref, effect_type)

        if fault is not None and fault.fault == "THROTTLE_429":
            # Documented pre-execution throttle: request not executed.
            return 429, {"error": "throttled", "retry_after_ms": 1000}, 0
        if fault is not None and fault.fault == "DROP_RESPONSE_BEFORE_COMMIT":
            raise WireDropped(committed=False)
        if fault is not None and fault.fault == "ERROR_5XX_NO_COMMIT":
            return 500, {"error": "internal"}, 0

        if self.profile == "C1" and idempotency_key is not None:
            for effect in self._effects:
                if effect["idempotency_key"] == idempotency_key:
                    # Declared replay semantics: cached response, no re-execution.
                    return 200, {**self._public(effect), "replayed": True}, 0

        # The refdest contract's one recognized, cited rejection shape: a
        # payload carrying reject=true is refused before any effect exists.
        if payload.get("reject") is True:
            return 400, {"error": "invalid_request", "detail": "reject flag"}, 0

        effect = self._insert_effect(effect_type, payload, client_ref, idempotency_key)
        if fault is not None and fault.fault == "DUPLICATE_ACCEPT":
            # Destination-internal duplication — impossible to induce
            # client-side against real APIs; refdest-only (adapters.md §2.3).
            self._insert_effect(effect_type, payload, client_ref, idempotency_key)
        if fault is not None and fault.fault == "DROP_RESPONSE_AFTER_COMMIT":
            raise WireDropped(committed=True)
        if fault is not None and fault.fault == "ERROR_5XX_AFTER_COMMIT":
            return 500, {"error": "internal"}, 0
        delay_ms = 0
        if fault is not None and fault.fault == "DELAY":
            delay_ms = int(fault.param.get("ms", 60_000))
            if not fault.param.get("commit", True):
                self._effects.remove(effect)
        return 201, {**self._public(effect), "replayed": False}, delay_ms

    def api_get(self, destination_ref: str) -> tuple[int, dict[str, Any], int]:
        if self.profile == "C3":
            raise CapabilityUnsupported("C3 profile has no status API")
        self._log("get", destination_ref=destination_ref)
        fault = self._active_fault("get", None, None)
        if fault is not None and fault.fault == "THROTTLE_429":
            return 429, {"error": "throttled"}, 0
        for effect in self._effects:
            if effect["destination_ref"] == destination_ref:
                return 200, self._public(effect), 0
        return 404, {"error": "not_found"}, 0  # authoritative absent

    def api_query_client_ref(self, client_ref: str) -> tuple[int, dict[str, Any], int]:
        if self.profile == "C3":
            raise CapabilityUnsupported("C3 profile has no query API")
        self._log("query", client_ref=client_ref)
        fault = self._active_fault("query", client_ref, None)
        if fault is not None and fault.fault == "THROTTLE_429":
            return 429, {"error": "throttled"}, 0
        matches = [
            self._public(e) for e in self._effects if e["client_ref"] == client_ref
        ]
        return 200, {"matches": matches}, 0

    def api_list(
        self, window_from: str, window_to: str, include_all: bool = False
    ) -> tuple[int, dict[str, Any], int]:
        if self.profile == "C3":
            raise CapabilityUnsupported("C3 profile has no list API")
        self._log("list", window_from=window_from, window_to=window_to)
        fault = self._active_fault("list", None, None)
        if fault is not None and fault.fault == "THROTTLE_429":
            return 429, {"error": "throttled"}, 0
        effects = [
            self._public(e)
            for e in self._effects
            if window_from <= e["created_at"] <= window_to
            and (include_all or not self.default_filter_quirk or e["visible_by_default"])
        ]
        return 200, {"effects": effects}, 0

    def api_notify(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any], int]:
        """C3 profile: fire-and-forget. 202, empty body, no ref, no query —
        but the truth log records the effect (the oracle's asymmetry)."""
        if self.profile != "C3":
            raise CapabilityUnsupported("notify exists only on the C3 profile")
        self._log("notify")
        fault = self._active_fault("notify", None, None)
        if fault is not None and fault.fault == "DROP_RESPONSE_BEFORE_COMMIT":
            raise WireDropped(committed=False)
        effect = self._insert_effect("notify", payload, None, None, via="notify")
        if fault is not None and fault.fault == "DUPLICATE_ACCEPT":
            self._insert_effect("notify", payload, None, None, via="notify")
        if fault is not None and fault.fault == "DROP_RESPONSE_AFTER_COMMIT":
            raise WireDropped(committed=True)
        _ = effect
        return 202, {}, 0

    # ── control plane (harness-only; adapters have no code path here) ─────────

    def control_schedule(self, entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            if entry["fault"] not in FAULT_KINDS:
                raise ValueError(f"unknown fault kind {entry['fault']!r}")
            self._schedule.append(
                _Fault(
                    fault=entry["fault"],
                    match=dict(entry["match"]),
                    param=dict(entry.get("param", {})),
                    once=bool(entry.get("once", True)),
                )
            )

    def control_reset(self, seed: int) -> None:
        self.__init__(  # type: ignore[misc]
            seed=seed, profile=self.profile,
            default_filter_quirk=self.default_filter_quirk,
            enrichment_quirk=self.enrichment_quirk,
        )

    def control_oob_create(
        self,
        effect_type: str,
        payload: dict[str, Any],
        client_ref: str | None = None,
    ) -> dict[str, Any]:
        """Out-of-band effect creation bypassing any client — the orphan-sweep
        oracle (testing.md §3.4). An optional client_ref lets the harness
        construct destination-internal duplicates for reconcile/audit tests."""
        return self._public(
            self._insert_effect(
                effect_type, payload, client_ref, None,
                visible_by_default=not self.default_filter_quirk, via="oob",
            )
        )

    def control_state(self) -> list[dict[str, Any]]:
        """Ground-truth dump — the destination read-back oracle."""
        return [dict(e) for e in self._effects]

    def control_log(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._request_log]


# ── The adapter over the refdest (in-process or HTTP transport) ───────────────


class RefdestAdapter(Adapter):
    """Adapter-protocol implementation bound to a refdest instance or server.

    Response classification is declaration-cited (RFC-002 §10): 201/200 → OK;
    the documented pre-execution 429 and the documented `invalid_request` 400
    → FAILED (side-effect-free per the refdest contract); EVERYTHING else —
    5xx, unrecognized shapes, dropped connections — maps to LOST/TIMEOUT, never
    FAILED.
    """

    def __init__(
        self,
        adapter_id: str,
        declaration: dict[str, Any],
        *,
        instance: RefDest | None = None,
        base_url: str | None = None,
    ) -> None:
        if (instance is None) == (base_url is None):
            raise ValueError("exactly one of instance/base_url is required")
        self.adapter_id = adapter_id
        self._declaration = declaration
        self._instance = instance
        self._base_url = base_url.rstrip("/") if base_url else None

    def declare(self) -> dict[str, Any]:
        return self._declaration

    def declaration_digest(self) -> str:
        return canonical_digest(self._declaration)

    # ── transport ─────────────────────────────────────────────────────────────

    def _call(
        self, op: str, deadline_s: float, **kwargs: Any
    ) -> tuple[int, dict[str, Any], int]:
        if self._instance is not None:
            method = getattr(self._instance, f"api_{op}")
            status, body, delay_ms = method(**kwargs)
            return int(status), dict(body), int(delay_ms)
        return self._call_http(op, deadline_s, **kwargs)

    def _call_http(
        self, op: str, deadline_s: float, **kwargs: Any
    ) -> tuple[int, dict[str, Any], int]:
        import json as _json
        import urllib.error
        import urllib.parse
        import urllib.request

        assert self._base_url is not None
        if op == "create":
            req = urllib.request.Request(
                f"{self._base_url}/effects",
                data=_json.dumps(kwargs).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        elif op == "notify":
            req = urllib.request.Request(
                f"{self._base_url}/notify",
                data=_json.dumps(kwargs).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        elif op == "get":
            req = urllib.request.Request(
                f"{self._base_url}/effects/{kwargs['destination_ref']}"
            )
        elif op == "query_client_ref":
            q = urllib.parse.urlencode({"client_ref": kwargs["client_ref"]})
            req = urllib.request.Request(f"{self._base_url}/effects?{q}")
        elif op == "list":
            q = urllib.parse.urlencode(
                {
                    "from": kwargs["window_from"],
                    "to": kwargs["window_to"],
                    "include_all": "true" if kwargs.get("include_all") else "false",
                }
            )
            req = urllib.request.Request(f"{self._base_url}/effects?{q}")
        else:  # pragma: no cover
            raise ValueError(f"unknown op {op}")
        try:
            with urllib.request.urlopen(req, timeout=deadline_s) as resp:
                body = _json.loads(resp.read() or b"{}")
                return resp.status, body, 0
        except urllib.error.HTTPError as err:
            return err.code, _json.loads(err.read() or b"{}"), 0
        except TimeoutError:
            raise
        except (urllib.error.URLError, ConnectionError, OSError) as err:
            raise WireDropped(committed=False) from err  # committed-ness unknown

    # ── protocol operations ───────────────────────────────────────────────────

    def dispatch(self, order: DispatchOrder, deadline_s: float) -> DispatchResult:
        request_digest = canonical_digest(
            {
                "op": "create",
                "effect_type": order.effect_type,
                "client_ref": order.client_ref,
                "payload_digest": canonical_digest(order.payload),
            }
        )
        base_evidence: dict[str, Any] = {
            "request_digest": request_digest,
            "adapter_id": self.adapter_id,
            "client_ref": order.client_ref,
        }
        try:
            if self._declaration["tier"] == "C3":
                status, body, delay_ms = self._call(
                    "notify", deadline_s, payload=order.payload
                )
            else:
                status, body, delay_ms = self._call(
                    "create",
                    deadline_s,
                    effect_type=order.effect_type,
                    payload=order.payload,
                    client_ref=order.client_ref,
                    idempotency_key=(
                        order.client_ref
                        if self._declaration["idempotency"]["supported"]
                        else None
                    ),
                )
        except WireDropped:
            return DispatchResult(
                "LOST",
                evidence={**base_evidence, "send_state": "sent_no_response"},
            )
        except TimeoutError:
            return DispatchResult(
                "TIMEOUT",
                evidence={**base_evidence, "deadline_s": deadline_s},
            )
        if delay_ms and delay_ms / 1000.0 > deadline_s:
            return DispatchResult(
                "TIMEOUT",
                evidence={**base_evidence, "deadline_s": deadline_s,
                          "delay_ms": delay_ms},
            )
        return self._classify(status, body, base_evidence)

    def _classify(
        self, status: int, body: dict[str, Any], evidence: dict[str, Any]
    ) -> DispatchResult:
        response_digest = canonical_digest(body)
        if status in (200, 201, 202):
            return DispatchResult(
                "OK",
                destination_ref=body.get("destination_ref"),
                response_digest=response_digest,
                evidence={**evidence, "status": status,
                          "replayed": bool(body.get("replayed"))},
            )
        if status == 429:
            # Declaration-cited: refdest throttles BEFORE execution — provably
            # side-effect-free, hence FAILED/RETRYABLE (adapters.md §1.3).
            return DispatchResult(
                "FAILED",
                failure_kind="RETRYABLE",
                response_digest=response_digest,
                evidence={**evidence, "status": status, "throttled": True},
            )
        if status == 400 and body.get("error") == "invalid_request":
            # Declaration-cited recognized rejection: no side effect.
            return DispatchResult(
                "FAILED",
                failure_kind="TERMINAL",
                response_digest=response_digest,
                evidence={**evidence, "status": status,
                          "destination_error": "invalid_request"},
            )
        # Everything else — 5xx, unknown status codes, unrecognized shapes —
        # is AMBIGUOUS territory: LOST, never FAILED (RFC-002 §10).
        return DispatchResult(
            "LOST",
            response_digest=response_digest,
            evidence={**evidence, "status": status, "unrecognized": True},
        )

    def status_query(
        self,
        *,
        client_ref: str | None = None,
        destination_ref: str | None = None,
        deadline_s: float = 10.0,
    ) -> StatusAnswer:
        if self._declaration["tier"] == "C3" or not self._declaration["queryable"][
            "supported"
        ]:
            raise CapabilityUnsupported(
                f"adapter {self.adapter_id}: declaration has no status query"
            )
        try:
            if destination_ref is not None:
                status, body, _ = self._call(
                    "get", deadline_s, destination_ref=destination_ref
                )
                if status == 200:
                    return StatusAnswer(
                        "PRESENT", 1, (body["destination_ref"],),
                        {"status": status, "response_digest": canonical_digest(body)},
                    )
                if status == 404:
                    return StatusAnswer(
                        "ABSENT", 0, (),
                        {"status": status, "authoritative_absent": True},
                    )
                return StatusAnswer("INDETERMINATE", None, (), {"status": status})
            if client_ref is not None:
                status, body, _ = self._call(
                    "query_client_ref", deadline_s, client_ref=client_ref
                )
                if status != 200:
                    return StatusAnswer("INDETERMINATE", None, (), {"status": status})
                matches = body["matches"]
                if matches:
                    return StatusAnswer(
                        "PRESENT",
                        len(matches),
                        tuple(m["destination_ref"] for m in matches),
                        {"status": status, "response_digest": canonical_digest(body)},
                    )
                return StatusAnswer(
                    "ABSENT", 0, (), {"status": status, "authoritative_absent": True}
                )
            raise ValueError("status_query needs client_ref or destination_ref")
        except (WireDropped, TimeoutError) as err:
            # A failed query is INDETERMINATE — never coerced to ABSENT.
            return StatusAnswer(
                "INDETERMINATE", None, (), {"transport_error": type(err).__name__}
            )

    def list_effects(
        self, window_from: str, window_to: str, deadline_s: float = 10.0
    ) -> list[dict[str, Any]]:
        if not self._declaration["list_queryable"]:
            raise CapabilityUnsupported(
                f"adapter {self.adapter_id}: declaration says list_queryable=false"
            )
        status, body, _ = self._call(
            "list",
            deadline_s,
            window_from=window_from,
            window_to=window_to,
            include_all=True,  # compensates the declared default-filter quirk
        )
        if status != 200:
            raise CapabilityUnsupported(f"list failed with status {status}")
        return list(body["effects"])
