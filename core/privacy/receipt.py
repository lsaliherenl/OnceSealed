"""Retirement receipt handed to the buyer once; the only place the salt exists in plain text.

Whoever holds the receipt can prove the retirement in the buyer's name, so the
buyer must keep it private and share it only when they choose to disclose.
"""

from typing import Any

from core.privacy.commitment import commitment, from_hex, to_hex
from core.privacy.identity import buyer_id, is_valid_lei

RECEIPT_VERSION = "receipt-v1"
BUNDLE_VERSION = "receipt-bundle-v1"
RECEIPT_WARNING = (
    "Keep this file private. Anyone holding it can prove this retirement in your name. "
    "Share it only when you want to disclose that you retired these credits."
)


def build_receipt(*, retirement_id: int, chain_id: int, contract: str, tx_hash: str, batch_id: bytes,
                  batch_key: str, start: int, end: int, lei: str, salt: bytes) -> dict[str, Any]:
    return {
        "version": RECEIPT_VERSION,
        "warning": RECEIPT_WARNING,
        "retirement_id": retirement_id,
        "chain_id": chain_id,
        "contract": contract,
        "tx_hash": tx_hash,
        "batch_key": batch_key,
        "batch_id": to_hex(batch_id),
        "start": start,
        "end": end,
        "lei": lei,
        "buyer_id": to_hex(buyer_id(lei)),
        "salt": to_hex(salt),
    }


def build_bundle(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    """One file for a purchase retired as several standard lots (each lot has its own salt)."""
    if not receipts or len({(r["lei"], r["chain_id"], r["contract"]) for r in receipts}) != 1:
        raise ValueError("a bundle holds receipts of one buyer on one contract")
    return {"version": BUNDLE_VERSION, "warning": RECEIPT_WARNING, "lei": receipts[0]["lei"],
            "buyer_id": receipts[0]["buyer_id"], "chain_id": receipts[0]["chain_id"],
            "contract": receipts[0]["contract"], "quantity": sum(r["end"] - r["start"] + 1 for r in receipts),
            "lots": receipts}


def receipt_commitment(receipt: dict[str, Any]) -> str:
    """Recompute the on-chain commitment from a receipt (offline check before calling verifyClaim)."""
    if not is_valid_lei(receipt["lei"]) or to_hex(buyer_id(receipt["lei"])) != receipt["buyer_id"].lower():
        raise ValueError("receipt LEI and buyer_id do not match")
    return to_hex(commitment(from_hex(receipt["buyer_id"]), from_hex(receipt["salt"]),
                             from_hex(receipt["batch_id"]), receipt["start"], receipt["end"]))
