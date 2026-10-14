"""End-to-end tests against a throwaway Anvil chain. Skipped if Foundry's anvil is not installed."""

import json
import random

import pytest
from eth_account import Account

from core.chain import anvil
from core.chain.registry import AuditStatus, Registry, RegistryError, connect
from core.config import PROJECT_ROOT, ROLES, ChainSettings
from core.data.batches import IssuanceBatch
from core.hashing import hash_json
from core.privacy.commitment import commitment, new_salt, to_hex
from core.privacy.identity import buyer_id, fictional_lei, project_id
from core.privacy.vault import VaultPayload, VaultStore, generate_keypair, seal, vault_hash
from core.service import OnceSealed

pytestmark = pytest.mark.skipif(anvil.anvil_binary() is None, reason="anvil not installed")


@pytest.fixture(scope="module")
def chain():
    port = anvil.free_port()
    proc = anvil.start_anvil(port)
    try:
        # Throwaway keys: the tests must not depend on .env (CI has none).
        keys = {role: "0x" + Account.create().key.hex().removeprefix("0x") for role in ROLES}
        w3, accounts = connect(ChainSettings("anvil", f"http://127.0.0.1:{port}", keys))
        anvil.fund(w3, [a.address for a in accounts.values()])
        yield w3, accounts
    finally:
        proc.terminate()


@pytest.fixture
def app(chain, tmp_path):
    w3, accounts = chain
    registry, _ = Registry.deploy(w3, accounts)
    pub, priv = generate_keypair()
    return OnceSealed(registry, VaultStore(tmp_path / "vault.sqlite"), pub, priv)


BATCH = IssuanceBatch("VCS1477", vintage=2020, batch_no=1, first_serial=1, last_serial=10_000)


def leis(n, seed=1):
    rng = random.Random(seed)
    return [fictional_lei(rng) for _ in range(n)]


def test_roles_granted(app):
    reg, accts = app.registry, app.registry.accounts
    for role, const in [("assessor", "ASSESSOR_ROLE"), ("operator", "OPERATOR_ROLE"), ("auditor", "AUDITOR_ROLE")]:
        role_id = getattr(reg.contract.functions, const)().call()
        assert reg.contract.functions.hasRole(role_id, accts[role].address).call()


def test_publish_report_anchors_published_file(app):
    report = json.loads((PROJECT_ROOT / "reports" / "VCS1477.json").read_text(encoding="utf-8"))
    version, _, rhash = app.publish_report(report)
    onchain = app.registry.get_report(project_id("VCS1477"), version)
    assert version == 1 and rhash == hash_json(report)
    assert to_hex(onchain.report_hash) == rhash and to_hex(onchain.method_hash) == report["method_hash"]
    assert onchain.score == report["overall"]["score"]


def test_full_flow_retire_overlap_audit_disclose(app):
    a_lei, b_lei = leis(2)
    app.ensure_batch(BATCH)
    assert app.ensure_batch(BATCH) is None  # idempotent

    a = app.retire(BATCH, 1, 500, a_lei)
    rec = app.public_record(a.retirement_id)
    assert rec.audit == AuditStatus.PENDING
    assert to_hex(rec.buyer_commitment) == to_hex(commitment(buyer_id(a_lei), bytes.fromhex(a.receipt["salt"][2:]),
                                                             BATCH.batch_id, 1, 500))

    with pytest.raises(RegistryError) as err:
        app.retire(BATCH, 400, 600, b_lei)
    assert err.value.name == "AlreadyRetired" and err.value.args_dict["conflictingRetirementId"] == a.retirement_id
    assert app.vault.get_by_retirement(app.chain_id, app.registry.address, a.retirement_id + 1) is None

    b = app.retire(BATCH, 501, 600, b_lei)
    assert app.registry.retirement_of(BATCH.batch_id, 500) == a.retirement_id
    assert app.registry.retirement_of(BATCH.batch_id, 501) == b.retirement_id

    result, tx = app.audit(a.retirement_id)
    assert result.valid and tx is not None and result.payload.lei == a_lei
    assert app.public_record(a.retirement_id).audit == AuditStatus.VERIFIED

    check = app.verify_receipt(a.receipt)
    assert check.valid and check.audit_status == AuditStatus.VERIFIED
    assert not app.verify_receipt({**a.receipt, "salt": to_hex(new_salt())}).valid
    assert not app.verify_receipt({**b.receipt, "retirement_id": a.retirement_id}).valid


def test_auditor_rejects_vault_that_does_not_match_commitment(app):
    """A dishonest operator commits to buyer A but seals buyer B's identity in the vault."""
    a_lei, b_lei = leis(2, seed=2)
    app.ensure_batch(BATCH)
    salt = new_salt()
    c = commitment(buyer_id(a_lei), salt, BATCH.batch_id, 1000, 1099)
    wrong = VaultPayload(batch_id=to_hex(BATCH.batch_id), start=1000, end=1099, lei=b_lei,
                         buyer_id=to_hex(buyer_id(b_lei)), salt=to_hex(salt))
    ct = seal(wrong, app.auditor_public)
    app.vault.put(ct)
    rid, _ = app.registry.retire(BATCH.batch_id, 1000, 1099, c, vault_hash(ct))

    result, tx = app.audit(rid)
    assert not result.valid and result.checks["commitment_matches_chain"] is False
    assert tx is not None and app.public_record(rid).audit == AuditStatus.REJECTED


def test_reverts_are_decoded(app):
    app.ensure_batch(BATCH)
    with pytest.raises(RegistryError) as err:
        app.retire(BATCH, 9_000, 20_000, leis(1, seed=3)[0])
    assert err.value.name == "InvalidRange"
    with pytest.raises(RegistryError) as err:
        app.registry.get_retirement(999)
    assert err.value.name == "UnknownRetirement"


def test_wrong_role_is_rejected_before_sending(app):
    reg = app.registry
    reg.accounts = {**reg.accounts, "operator": reg.accounts["assessor"]}  # assessor tries to act as operator
    with pytest.raises(RegistryError) as err:
        reg.register_batch(b"\x01" * 32, b"\x02" * 32, 1, 10)
    assert err.value.name == "AccessControlUnauthorizedAccount"
