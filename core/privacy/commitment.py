"""Buyer commitment, identical to RetirementRegistry.commitmentOf.

    commitment = keccak256(abi.encode(buyerId, salt, batchId, start, end))

Binding the range means a disclosed salt proves exactly one retirement.
"""

import secrets

from eth_abi import encode
from eth_utils import keccak

SALT_BYTES = 32


def new_salt() -> bytes:
    return secrets.token_bytes(SALT_BYTES)


def _b32(value: bytes, name: str) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError(f"{name} must be 32 bytes")
    return value


def commitment(buyer_id: bytes, salt: bytes, batch_id: bytes, start: int, end: int) -> bytes:
    if not 0 <= start <= end < 2**64:
        raise ValueError(f"invalid range {start}-{end}")
    return keccak(encode(
        ["bytes32", "bytes32", "bytes32", "uint64", "uint64"],
        [_b32(buyer_id, "buyer_id"), _b32(salt, "salt"), _b32(batch_id, "batch_id"), start, end],
    ))


def to_hex(b: bytes) -> str:
    return "0x" + b.hex()


def from_hex(h: str) -> bytes:
    return bytes.fromhex(h[2:] if h.startswith("0x") else h)
