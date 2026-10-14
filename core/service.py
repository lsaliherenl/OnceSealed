"""High-level flows that combine the privacy layer with the chain. The Streamlit app calls these.

    publish_report   anchor a published quality report (hash, score, method hash)
    retire           commitment + sealed vault + on-chain retirement + buyer receipt
    audit            open the vault, check it against the chain, attest on-chain
    verify_receipt   selective disclosure: anyone checks a receipt against the chain
"""

from dataclasses import dataclass
from typing import Any

from core.chain.registry import AuditStatus, Registry, RegistryError, Retirement, TxResult
from core.data.batches import IssuanceBatch
from core.hashing import hash_json
from core.privacy.commitment import commitment, from_hex, new_salt, to_hex
from core.privacy.identity import buyer_id, project_id
from core.privacy.receipt import build_receipt, receipt_commitment
from core.privacy.vault import AuditResult, VaultPayload, VaultStore, audit, seal, vault_hash


@dataclass(frozen=True)
class RetireOutcome:
    retirement_id: int
    tx: TxResult
    receipt: dict[str, Any]
    vault_hash: str
    serial_label: str


@dataclass(frozen=True)
class ClaimCheck:
    valid: bool
    checks: dict[str, bool]
    audit_status: AuditStatus | None
    error: str | None = None


class OnceSealed:
    def __init__(self, registry: Registry, vault: VaultStore, auditor_public_b64: str,
                 auditor_private_b64: str | None = None):
        self.registry = registry
        self.vault = vault
        self.auditor_public = auditor_public_b64
        self.auditor_private = auditor_private_b64
        self.chain_id = registry.w3.eth.chain_id

    # --- setup ------------------------------------------------------------------------------

    def ensure_batch(self, batch: IssuanceBatch) -> TxResult | None:
        if self.registry.batch_exists(batch.batch_id):
            return None
        return self.registry.register_batch(batch.batch_id, batch.project_id_bytes, batch.first_serial,
                                            batch.last_serial)

    def publish_report(self, report: dict[str, Any]) -> tuple[int, TxResult, str]:
        """Anchor a report exactly as published in reports/<id>.json. Returns (version, tx, report_hash)."""
        score = report["overall"]["score"]
        if score is None:
            raise ValueError("report has no overall score; nothing to anchor")
        report_hash = hash_json(report)
        version, tx = self.registry.register_quality_report(
            project_id(report["project"]["project_id"]), from_hex(report_hash), int(score),
            from_hex(report["method_hash"]))
        return version, tx, report_hash

    # --- retirement -------------------------------------------------------------------------

    def retire(self, batch: IssuanceBatch, start: int, end: int, lei: str) -> RetireOutcome:
        """Retire [start, end] for the buyer identified by `lei`. The salt leaves only inside the receipt."""
        bid, salt = buyer_id(lei), new_salt()
        c = commitment(bid, salt, batch.batch_id, start, end)
        payload = VaultPayload(batch_id=to_hex(batch.batch_id), start=start, end=end, lei=lei,
                               buyer_id=to_hex(bid), salt=to_hex(salt))
        ciphertext = seal(payload, self.auditor_public)
        vh = vault_hash(ciphertext)

        # Fail before storing anything if the chain would reject it (overlap, outside batch, ...).
        self.registry.simulate_retire(batch.batch_id, start, end, c, vh)
        stored = self.vault.put(ciphertext)
        retirement_id, tx = self.registry.retire(batch.batch_id, start, end, c, vh)
        self.vault.link(stored, self.chain_id, self.registry.address, retirement_id)

        receipt = build_receipt(retirement_id=retirement_id, chain_id=self.chain_id,
                                contract=self.registry.address, tx_hash=tx.tx_hash, batch_id=batch.batch_id,
                                batch_key=batch.key, start=start, end=end, lei=lei, salt=salt)
        return RetireOutcome(retirement_id, tx, receipt, stored, batch.serial_label(start, end))

    # --- audit ------------------------------------------------------------------------------

    def audit(self, retirement_id: int, attest: bool = True) -> tuple[AuditResult, TxResult | None]:
        if not self.auditor_private:
            raise RuntimeError("auditor private key is not available on this machine")
        record = self.registry.get_retirement(retirement_id)
        ciphertext = self.vault.get_by_retirement(self.chain_id, self.registry.address, retirement_id)
        if ciphertext is None:
            ciphertext = self.vault.get(to_hex(record.audit_vault_hash))
        if ciphertext is None:
            return AuditResult(False, {"vault_found": False}, None, "no vault stored for this retirement"), None
        result = audit(ciphertext, record.onchain_dict(), self.auditor_private)
        tx = None
        if attest and record.audit == AuditStatus.PENDING:
            tx = self.registry.attest(retirement_id, result.valid)
        return result, tx

    # --- public views -----------------------------------------------------------------------

    def public_record(self, retirement_id: int) -> Retirement:
        """What anyone can see: range, commitment, vault hash, report version, audit status. No identity."""
        return self.registry.get_retirement(retirement_id)

    def verify_receipt(self, receipt: dict[str, Any]) -> ClaimCheck:
        checks: dict[str, bool] = {}
        try:
            checks["same_chain_and_contract"] = (
                receipt["chain_id"] == self.chain_id
                and receipt["contract"].lower() == self.registry.address.lower())
            record = self.registry.get_retirement(int(receipt["retirement_id"]))
            checks["range_matches_chain"] = (
                receipt["batch_id"].lower() == to_hex(record.batch_id)
                and receipt["start"] == record.start and receipt["end"] == record.end)
            checks["receipt_matches_commitment"] = receipt_commitment(receipt) == to_hex(record.buyer_commitment)
            checks["contract_verify_claim"] = self.registry.verify_claim(
                record.retirement_id, from_hex(receipt["buyer_id"]), from_hex(receipt["salt"]))
        except (KeyError, ValueError, TypeError, RegistryError) as e:
            return ClaimCheck(False, checks, None, f"{e.__class__.__name__}: {e}")
        return ClaimCheck(all(checks.values()), checks, record.audit)
