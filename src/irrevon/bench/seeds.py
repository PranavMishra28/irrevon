"""Deterministic seed derivation — preregistration §3.4, byte-level pinning.

    seed(cell, replicate) = first 8 bytes, big-endian, of
    SHA-256(master_seed ‖ "irrevonbench/v1" ‖ cell_id ‖ replicate_index)

The preregistration pins the formula but not the byte encoding of ``‖``; this
module pins it (recorded in ADR-0030): fields are UTF-8 encoded and joined with
the ASCII unit separator 0x1F, which removes cross-field ambiguity (a cell_id
ending in a digit can never collide with a longer replicate index).
``master_seed`` is the 64-char lowercase-hex string itself (not its raw bytes),
``replicate_index`` is its decimal ASCII form. Arm identity is NOT an input —
cross-arm pairing by construction (§5.1).
"""

from __future__ import annotations

import hashlib
import re
from typing import Final

__all__ = ["DOMAIN_TAG", "MASTER_SEED_RE", "derive_seed"]

DOMAIN_TAG: Final = "irrevonbench/v1"
MASTER_SEED_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_SEP: Final = b"\x1f"


def derive_seed(master_seed: str, cell_id: str, replicate_index: int) -> int:
    """Non-negative 64-bit seed for one (cell, replicate)."""
    if not MASTER_SEED_RE.match(master_seed):
        raise ValueError("master_seed must be a 64-char lowercase-hex string")
    if not cell_id:
        raise ValueError("cell_id must be non-empty")
    if not isinstance(replicate_index, int) or isinstance(replicate_index, bool):
        raise ValueError("replicate_index must be an int")
    if replicate_index < 0:
        raise ValueError("replicate_index must be non-negative")
    material = _SEP.join(
        [
            master_seed.encode("utf-8"),
            DOMAIN_TAG.encode("utf-8"),
            cell_id.encode("utf-8"),
            str(replicate_index).encode("utf-8"),
        ]
    )
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:8], "big")
