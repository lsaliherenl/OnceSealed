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


LOT_BATCH = IssuanceBatch("VCS1477", vintage=2021, batch_no=1, first_serial=1, last_serial=1_050, lot_size=100)


def test_lot_batch_splits_purchase_into_unlinkable_lots(app):
    a_lei, b_lei = leis(2, seed=4)
    app.ensure_batch(LOT_BATCH)
    assert app.registry.get_batch(LOT_BATCH.batch_id).lot_size == 100

    out = app.retire_lots(LOT_BATCH, 1, 300, a_lei)
    assert [(o.receipt["start"], o.receipt["end"]) for o in out.lots] == [(1, 100), (101, 200), (201, 300)]
    commitments = {to_hex(app.public_record(o.retirement_id).buyer_commitment) for o in out.lots}
    assert len(commitments) == 3  # different salts: nothing on-chain ties the three lots together
    assert app.verify_receipt(out.receipt).valid

    app.retire_lots(LOT_BATCH, 501, 600, b_lei)
    count = app.registry.retirement_count()
    with pytest.raises(RegistryError) as err:  # 401-500 is free but 501-600 is taken: nothing at all is sent
        app.retire_lots(LOT_BATCH, 401, 600, b_lei)
    assert err.value.name == "AlreadyRetired" and app.registry.retirement_count() == count
    with pytest.raises(ValueError, match="lot boundary"):
        app.retire_lots(LOT_BATCH, 650, 749, b_lei)
    with pytest.raises(RegistryError) as err:  # the contract enforces the rule even without the client check
        app.retire(LOT_BATCH, 650, 749, b_lei)
    assert err.value.name == "NotALot"
    tail = app.retire_lots(LOT_BATCH, 1001, 1050, b_lei)  # the batch's final lot may be shorter
    assert app.registry.retirement_of(LOT_BATCH.batch_id, 1050) == tail.lots[0].retirement_id

    for o in out.lots:
        assert app.audit(o.retirement_id)[0].valid
    assert app.verify_receipt(out.receipt).audit_status == AuditStatus.VERIFIED
    swapped = {**out.receipt, "lots": [*out.receipt["lots"][:2], tail.receipt]}  # another buyer's lot slipped in
    assert not app.verify_receipt(swapped).valid


def test_event_index_matches_contract_views(app):
    """Free-range batches: hints and lookups from the CreditRetired index equal the contract's list walk."""
    batch = IssuanceBatch("VCS1477", vintage=2022, batch_no=1, first_serial=1, last_serial=5_000)
    app.ensure_batch(batch)
    rng = random.Random(11)
    reg, done = app.registry, 0
    for _ in range(200):  # random ranges in random order; overlapping ones are rejected by the contract
        s = rng.randint(1, 4_950)
        try:
            reg.retire(batch.batch_id, s, s + rng.randint(0, 40), new_salt(), new_salt())
            done += 1
        except RegistryError as err:
            assert err.name == "AlreadyRetired"
        if done == 25:
            break
    assert done == 25
    fresh = Registry(reg.w3, reg.address, reg.accounts)  # rebuilt purely from logs
    for serial in [1, 5_000, *(rng.randint(1, 5_000) for _ in range(300))]:
        on_chain = reg.contract.functions.retirementOf(batch.batch_id, serial).call()
        assert reg.retirement_of(batch.batch_id, serial) == on_chain == fresh.retirement_of(batch.batch_id, serial)
        assert fresh.hint_for(batch.batch_id, serial) == reg.contract.functions.hintFor(batch.batch_id, serial).call()


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
