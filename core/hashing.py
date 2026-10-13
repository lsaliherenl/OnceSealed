"""Canonical JSON and keccak256, shared by reports and the chain client.

Anyone can recompute a hash with: keccak256(canonical_json(obj)).
"""

import json
from typing import Any

from eth_utils import keccak


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def keccak_hex(data: bytes) -> str:
    return "0x" + keccak(data).hex()


def hash_json(obj: Any) -> str:
    return keccak_hex(canonical_json(obj))
