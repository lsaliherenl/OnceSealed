"""Auditor vault: the buyer's identity, sealed to the auditor's public key and kept off-chain.

Only keccak256(ciphertext) goes on-chain (auditVaultHash). The auditor opens the
vault with their private key, recomputes the commitment and compares both hashes
with the chain before attesting.

Sealed boxes (libsodium) use a fresh ephemeral key per message: the operator can
encrypt to the auditor but cannot decrypt afterwards, and two vaults with the
same content have different ciphertexts.
"""

import base64
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from eth_utils import keccak
from nacl.exceptions import CryptoError
from nacl.public import PrivateKey, PublicKey, SealedBox

from core.hashing import canonical_json
from core.privacy.commitment import commitment, from_hex, to_hex
from core.privacy.identity import buyer_id, is_valid_lei

VAULT_VERSION = "vault-v1"


@dataclass(frozen=True)
class VaultPayload:
    batch_id: str  # 0x-hex bytes32
    start: int
    end: int
    lei: str
    buyer_id: str  # 0x-hex bytes32
    salt: str  # 0x-hex bytes32
    version: str = VAULT_VERSION

    def to_bytes(self) -> bytes:
        return canonical_json(asdict(self))

    @classmethod
    def from_bytes(cls, data: bytes) -> "VaultPayload":
        return cls(**json.loads(data.decode("utf-8")))


def generate_keypair() -> tuple[str, str]:
    """(public, private) as base64 strings for .env."""
    sk = PrivateKey.generate()
    return base64.b64encode(bytes(sk.public_key)).decode(), base64.b64encode(bytes(sk)).decode()


def seal(payload: VaultPayload, auditor_public_b64: str) -> bytes:
    return SealedBox(PublicKey(base64.b64decode(auditor_public_b64))).encrypt(payload.to_bytes())


def open_vault(ciphertext: bytes, auditor_private_b64: str) -> VaultPayload:
    return VaultPayload.from_bytes(SealedBox(PrivateKey(base64.b64decode(auditor_private_b64))).decrypt(ciphertext))


def vault_hash(ciphertext: bytes) -> bytes:
    return keccak(ciphertext)


@dataclass(frozen=True)
class AuditResult:
    valid: bool
    checks: dict[str, bool]
    payload: VaultPayload | None
    error: str | None = None


def audit(ciphertext: bytes, onchain: dict, auditor_private_b64: str) -> AuditResult:
    """Check a vault against an on-chain retirement record.

    ``onchain`` holds the contract's fields as 0x-hex / ints: batchId, start, end,
    buyerCommitment, auditVaultHash.
    """
    checks = {"vault_hash_matches_chain": to_hex(vault_hash(ciphertext)) == onchain["auditVaultHash"].lower()}
    try:
        p = open_vault(ciphertext, auditor_private_b64)
    except (CryptoError, ValueError, TypeError) as e:
        return AuditResult(False, {**checks, "vault_opens": False}, None, f"{e.__class__.__name__}: {e}")
    checks["vault_opens"] = True
    checks["range_matches_chain"] = (
        p.batch_id.lower() == onchain["batchId"].lower() and p.start == onchain["start"] and p.end == onchain["end"]
    )
    checks["lei_valid"] = is_valid_lei(p.lei)
    checks["buyer_id_matches_lei"] = checks["lei_valid"] and to_hex(buyer_id(p.lei)) == p.buyer_id.lower()
    recomputed = commitment(from_hex(p.buyer_id), from_hex(p.salt), from_hex(p.batch_id), p.start, p.end)
    checks["commitment_matches_chain"] = to_hex(recomputed) == onchain["buyerCommitment"].lower()
    return AuditResult(all(checks.values()), checks, p)


class VaultStore:
    """Off-chain storage of ciphertexts, keyed by their on-chain hash."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS vault ("
                " vault_hash TEXT PRIMARY KEY, ciphertext BLOB NOT NULL, created_at TEXT NOT NULL,"
                " chain_id INTEGER, contract TEXT, retirement_id INTEGER)"
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def put(self, ciphertext: bytes) -> str:
        h = to_hex(vault_hash(ciphertext))
        with self._conn() as c:
            c.execute("INSERT INTO vault (vault_hash, ciphertext, created_at) VALUES (?, ?, ?)",
                      (h, ciphertext, datetime.now(timezone.utc).isoformat()))
        return h

    def link(self, vault_hash_hex: str, chain_id: int, contract: str, retirement_id: int) -> None:
        with self._conn() as c:
            cur = c.execute("UPDATE vault SET chain_id = ?, contract = ?, retirement_id = ? WHERE vault_hash = ?",
                            (chain_id, contract.lower(), retirement_id, vault_hash_hex.lower()))
            if cur.rowcount != 1:
                raise KeyError(vault_hash_hex)

    def get(self, vault_hash_hex: str) -> bytes | None:
        with self._conn() as c:
            row = c.execute("SELECT ciphertext FROM vault WHERE vault_hash = ?", (vault_hash_hex.lower(),)).fetchone()
        return row[0] if row else None

    def get_by_retirement(self, chain_id: int, contract: str, retirement_id: int) -> bytes | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT ciphertext FROM vault WHERE chain_id = ? AND contract = ? AND retirement_id = ?",
                (chain_id, contract.lower(), retirement_id),
            ).fetchone()
        return row[0] if row else None
