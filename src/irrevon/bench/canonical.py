"""Canonical bytes, digests, and the manifest root hash (preregistration §3.1).

Frozen artifacts are RFC 8785 (JCS) canonical JSON; artifact digests are SHA-256
over those canonical bytes; the manifest root hash is SHA-256 over the JCS bytes
of the sorted ``[path, sha256]`` pairs — deterministic, order-independent, and
recomputable by any third party from the files alone.
"""

from __future__ import annotations

import hashlib
from typing import Any

from irrevon.identity import canonical_bytes

__all__ = [
    "artifact_sha256",
    "canonical_json_text",
    "manifest_root_hash",
    "sha256_hex",
]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_text(value: object) -> str:
    """The exact text form frozen artifacts are written in (JCS + newline)."""
    return canonical_bytes(value).decode("utf-8") + "\n"


def artifact_sha256(value: object) -> str:
    """Digest of an artifact's canonical bytes (NOT of its on-disk file bytes,
    so incidental whitespace can never change an artifact's identity)."""
    return sha256_hex(canonical_bytes(value))


def manifest_root_hash(artifacts: list[dict[str, Any]]) -> str:
    """Root hash over sorted (path, sha256) pairs of a manifest's artifact list."""
    pairs = sorted([a["path"], a["sha256"]] for a in artifacts)
    return sha256_hex(canonical_bytes(pairs))
