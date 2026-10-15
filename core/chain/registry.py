"""Deploy and talk to RetirementRegistry.

Every write is simulated first (eth_call from the sending role), so a revert surfaces
as a readable ``RegistryError`` such as ``AlreadyRetired(conflictingRetirementId=1)``
before any gas is spent.
"""

import json
import os
import time
from dataclasses import dataclass
from enum import IntEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from eth_abi import decode
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import keccak
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import BadFunctionCallOutput, ContractCustomError, ContractLogicError

from core.config import ChainSettings

ARTIFACT_PATH = Path(__file__).parent / "artifacts" / "RetirementRegistry.json"
ROLE_NAMES = {"assessor": "ASSESSOR_ROLE", "operator": "OPERATOR_ROLE", "auditor": "AUDITOR_ROLE"}
DEFAULT_ADMIN_DELAY = 2 * 24 * 3600  # an admin handover must wait two days before it can be accepted


@lru_cache(maxsize=1)
def load_artifact() -> dict[str, Any]:
    # ONCESEALED_ARTIFACT lets the scale experiment deploy an older contract version for comparison.
    path = Path(os.environ.get("ONCESEALED_ARTIFACT", ARTIFACT_PATH))
    return json.loads(path.read_text(encoding="utf-8"))


class AuditStatus(IntEnum):
    PENDING = 0
    VERIFIED = 1
    REJECTED = 2


@dataclass(frozen=True)
class Retirement:
    retirement_id: int
    batch_id: bytes
    start: int
    end: int
    buyer_commitment: bytes
    audit_vault_hash: bytes
    report_version: int
    retired_at: int
    audit: AuditStatus

    def onchain_dict(self) -> dict[str, Any]:
        """Fields in the hex/int form used by core.privacy.vault.audit."""
        return {"batchId": "0x" + self.batch_id.hex(), "start": self.start, "end": self.end,
                "buyerCommitment": "0x" + self.buyer_commitment.hex(),
                "auditVaultHash": "0x" + self.audit_vault_hash.hex()}


@dataclass(frozen=True)
class Batch:
    batch_id: bytes
    project_id: bytes
    first_serial: int
    last_serial: int
    lot_size: int = 0  # 0 = free ranges; otherwise each retirement is exactly one aligned lot


@dataclass(frozen=True)
class Report:
    project_id: bytes
    version: int
    report_hash: bytes
    method_hash: bytes
    score: int
    registered_at: int


@dataclass(frozen=True)
class TxResult:
    tx_hash: str
    block_number: int
    gas_used: int
    receipt: Any


class RegistryError(RuntimeError):
    """A contract revert decoded from its custom error."""

    def __init__(self, name: str, args: dict[str, Any], raw: str | None = None):
        self.name, self.args_dict, self.raw = name, args, raw
        detail = ", ".join(f"{k}={_fmt(v)}" for k, v in args.items())
        super().__init__(f"{name}({detail})")


def _fmt(v: Any) -> str:
    return "0x" + v.hex() if isinstance(v, bytes) else str(v)


def _error_table(abi: list[dict[str, Any]]) -> dict[bytes, tuple[str, list[str], list[str]]]:
    table = {}
    for e in abi:
        if e["type"] != "error":
            continue
        types = [i["type"] for i in e["inputs"]]
        selector = keccak(text=f"{e['name']}({','.join(types)})")[:4]
        table[selector] = (e["name"], [i["name"] for i in e["inputs"]], types)
    return table


def decode_revert(data: str | bytes | None, abi: list[dict[str, Any]]) -> RegistryError:
    if isinstance(data, str):
        data = bytes.fromhex(data[2:] if data.startswith("0x") else data)
    if not data or len(data) < 4:
        return RegistryError("Reverted", {}, None)
    entry = _error_table(abi).get(data[:4])
    if entry is None:
        return RegistryError("UnknownError", {"data": data}, "0x" + data.hex())
    name, names, types = entry
    values = decode(types, data[4:]) if types else ()
    return RegistryError(name, dict(zip(names, values)), "0x" + data.hex())


def connect(settings: ChainSettings) -> tuple[Web3, dict[str, LocalAccount]]:
    w3 = Web3(Web3.HTTPProvider(settings.rpc_url, request_kwargs={"timeout": 60}))
    if not w3.is_connected():
        raise ConnectionError(f"cannot reach {settings.network} RPC at {settings.rpc_url}")
    accounts = {role: Account.from_key(key) for role, key in settings.private_keys.items()}
    return w3, accounts


class Registry:
    def __init__(self, w3: Web3, address: str, accounts: dict[str, LocalAccount]):
        self.w3 = w3
        self.accounts = accounts
        self.abi = load_artifact()["abi"]
        self.contract: Contract = w3.eth.contract(address=Web3.to_checksum_address(address), abi=self.abi)
        self.address = self.contract.address

    # --- deployment -------------------------------------------------------------------------

    @classmethod
    def deploy(cls, w3: Web3, accounts: dict[str, LocalAccount],
               admin_delay: int = DEFAULT_ADMIN_DELAY) -> tuple["Registry", TxResult]:
        """Deploy with the deployer as admin (two-step handover after `admin_delay` seconds),
        then grant the three working roles."""
        art = load_artifact()
        deployer = accounts["deployer"]
        factory = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
        ctor = next((e for e in art["abi"] if e["type"] == "constructor"), {"inputs": []})
        args = (admin_delay, deployer.address) if len(ctor["inputs"]) == 2 else (deployer.address,)
        tx = factory.constructor(*args).build_transaction(_base_tx(w3, deployer))
        result = _send(w3, deployer, tx, art["abi"])
        reg = cls(w3, result.receipt["contractAddress"], accounts)
        reg.grant_roles()
        return reg, result

    def grant_roles(self) -> list[TxResult]:
        """Grant the working roles that are still missing (safe to re-run after an interrupted deploy).
        Role ids are computed locally: a load-balanced public RPC may not see a just-deployed contract yet."""
        done = []
        for role, const in ROLE_NAMES.items():
            role_id = keccak(text=const)
            addr = self.accounts[role].address
            if _retry(lambda: self.contract.functions.hasRole(role_id, addr).call()):
                continue
            done.append(self._transact("deployer", self.contract.functions.grantRole(role_id, addr)))
        return done

    # --- writes -----------------------------------------------------------------------------

    def _transact(self, role: str, fn) -> TxResult:
        acct = self.accounts[role]
        try:
            fn.call({"from": acct.address})  # simulate: surface reverts before spending gas
        except (ContractCustomError, ContractLogicError) as e:
            raise decode_revert(getattr(e, "data", None), self.abi) from None
        return _send(self.w3, acct, fn.build_transaction(_base_tx(self.w3, acct)), self.abi)

    def register_batch(self, batch_id: bytes, project_id: bytes, first: int, last: int,
                       lot_size: int = 0) -> TxResult:
        fn = next(e for e in self.abi if e.get("type") == "function" and e.get("name") == "registerBatch")
        if len(fn["inputs"]) == 5:
            call = self.contract.functions.registerBatch(batch_id, project_id, first, last, lot_size)
        elif lot_size == 0:  # older contract versions (scale experiment) have no lot sizes
            call = self.contract.functions.registerBatch(batch_id, project_id, first, last)
        else:
            raise ValueError("this contract version does not support lot sizes")
        return self._transact("operator", call)

    def register_quality_report(self, project_id: bytes, report_hash: bytes, score: int,
                                method_hash: bytes) -> tuple[int, TxResult]:
        res = self._transact("assessor", self.contract.functions.registerQualityReport(
            project_id, report_hash, score, method_hash))
        ev = self.contract.events.QualityReportRegistered().process_receipt(res.receipt)
        return ev[0]["args"]["version"], res

    def hint_for(self, batch_id: bytes, start: int) -> int:
        """Predecessor retirement for a new range (walks the list in an eth_call; fine at demo scale,
        large batches would derive it from CreditRetired events)."""
        return self._call(self.contract.functions.hintFor(batch_id, start)) if self.uses_hints else 0

    def retire(self, batch_id: bytes, start: int, end: int, commitment: bytes,
               vault_hash: bytes) -> tuple[int, TxResult]:
        fn = self.retire_fn(batch_id, start, end, commitment, vault_hash, self.hint_for(batch_id, start))
        res = self._transact("operator", fn)
        ev = self.contract.events.CreditRetired().process_receipt(res.receipt)
        return ev[0]["args"]["retirementId"], res

    @property
    def uses_hints(self) -> bool:
        """True if this contract version takes a prevHint argument in retire()."""
        fn = next(e for e in self.abi if e.get("type") == "function" and e.get("name") == "retire")
        return len(fn["inputs"]) == 6

    def retire_fn(self, batch_id: bytes, start: int, end: int, commitment: bytes, vault_hash: bytes,
                  prev_hint: int = 0):
        """The retire() call for either contract version (used by the scale replay)."""
        if self.uses_hints:
            return self.contract.functions.retire(batch_id, start, end, commitment, vault_hash, prev_hint)
        return self.contract.functions.retire(batch_id, start, end, commitment, vault_hash)

    def simulate_retire(self, batch_id: bytes, start: int, end: int, commitment: bytes, vault_hash: bytes) -> None:
        """Raise RegistryError if retire would revert (e.g. overlap), without sending."""
        try:
            self.retire_fn(batch_id, start, end, commitment, vault_hash, self.hint_for(batch_id, start)).call(
                {"from": self.accounts["operator"].address})
        except (ContractCustomError, ContractLogicError) as e:
            raise decode_revert(getattr(e, "data", None), self.abi) from None

    def attest(self, retirement_id: int, valid: bool) -> TxResult:
        return self._transact("auditor", self.contract.functions.attestRetirement(retirement_id, valid))

    # --- reads ------------------------------------------------------------------------------

    def _call(self, fn):
        try:
            return fn.call()
        except (ContractCustomError, ContractLogicError) as e:
            raise decode_revert(getattr(e, "data", None), self.abi) from None

    def get_retirement(self, retirement_id: int) -> Retirement:
        r = self._call(self.contract.functions.getRetirement(retirement_id))
        return Retirement(retirement_id, r[0], r[1], r[2], r[3], r[4], r[5], r[6], AuditStatus(r[7]))

    def get_batch(self, batch_id: bytes) -> Batch:
        b = self._call(self.contract.functions.getBatch(batch_id))
        return Batch(batch_id, b[0], b[1], b[2], b[3] if len(b) > 4 else 0)

    def batch_exists(self, batch_id: bytes) -> bool:
        try:
            self.get_batch(batch_id)
            return True
        except RegistryError as e:
            if e.name == "UnknownBatch":
                return False
            raise

    def batch_retirements(self, batch_id: bytes) -> list[int]:
        return list(self._call(self.contract.functions.batchRetirements(batch_id)))

    def ordered_retirements(self, batch_id: bytes) -> list[int]:
        """Retirement ids of a batch in serial order."""
        return list(self._call(self.contract.functions.orderedRetirements(batch_id)))

    def retirement_of(self, batch_id: bytes, serial: int) -> int:
        return self._call(self.contract.functions.retirementOf(batch_id, serial))

    def retirement_count(self) -> int:
        return self._call(self.contract.functions.retirementCount())

    def report_count(self, project_id: bytes) -> int:
        return self._call(self.contract.functions.reportCount(project_id))

    def get_report(self, project_id: bytes, version: int) -> Report:
        r = self._call(self.contract.functions.getReport(project_id, version))
        return Report(project_id, version, r[0], r[1], r[2], r[3])

    def verify_claim(self, retirement_id: int, buyer_id: bytes, salt: bytes) -> bool:
        return self._call(self.contract.functions.verifyClaim(retirement_id, buyer_id, salt))


def _retry(fn, attempts: int = 8, delay: float = 1.5):
    """Read through a load-balanced RPC: a node that is a block behind returns empty data for new state."""
    for i in range(attempts):
        try:
            return fn()
        except BadFunctionCallOutput:
            if i == attempts - 1:
                raise
            time.sleep(delay)


def _base_tx(w3: Web3, acct: LocalAccount) -> dict[str, Any]:
    return {"from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address, "pending")}


def _send(w3: Web3, acct: LocalAccount, tx: dict[str, Any], abi: list[dict[str, Any]]) -> TxResult:
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    if receipt["status"] != 1:
        raise RegistryError("TransactionFailed", {"tx": tx_hash.hex()})
    if w3.eth.chain_id != 31337:
        # A load-balanced public RPC can route the next read to a node that has not seen this block yet;
        # wait until the RPC reports a later block so the next simulation sees the new state.
        for _ in range(20):
            if w3.eth.block_number > receipt["blockNumber"]:
                break
            time.sleep(1.5)
    return TxResult("0x" + bytes(tx_hash).hex(), receipt["blockNumber"], receipt["gasUsed"], receipt)
