import json
import random
from pathlib import Path

import pytest

from core.privacy.commitment import commitment, from_hex, new_salt, to_hex
from core.privacy.identity import buyer_id, fictional_lei, is_valid_lei, lei_check_digits, project_id, text_id
from core.privacy.receipt import build_receipt, receipt_commitment
from core.privacy.vault import VaultPayload, VaultStore, audit, generate_keypair, open_vault, seal, vault_hash

VECTORS = json.loads((Path(__file__).parent / "vectors.json").read_text(encoding="utf-8"))
BATCH = text_id("VCS1477|batch-1")


# --- identity -----------------------------------------------------------------------------------

def test_lei_checksum():
    base = "ONCE00SEALEDDEMO01"  # fictional; we never use real LEIs, even in tests
    lei = base + lei_check_digits(base)
    assert is_valid_lei(lei)
    # ISO 7064 MOD 97-10: the whole code, letters as 10..35, is congruent to 1 mod 97
    assert int("".join(str(int(c, 36)) for c in lei)) % 97 == 1
    wrong = base + f"{(int(lei[-2:]) + 1) % 100:02d}"
    assert not is_valid_lei(wrong)
    assert not is_valid_lei(lei.lower())
    assert not is_valid_lei(lei[:-1])


def test_fictional_leis_are_valid_and_random():
    rng = random.Random(1)
    leis = {fictional_lei(rng) for _ in range(200)}
    assert len(leis) == 200
    assert all(is_valid_lei(lei) and lei[4:6] == "00" for lei in leis)


def test_buyer_id_rejects_invalid_lei_and_normalizes_case():
    lei = fictional_lei(random.Random(2))
    assert buyer_id(lei.lower()) == buyer_id(lei)
    with pytest.raises(ValueError):
        buyer_id("NOT-A-LEI")


def test_project_id_uses_offsetsdb_format():
    assert project_id("VCS1477") == text_id("VCS1477")
    with pytest.raises(ValueError):
        project_id("VCS-1477")


# --- shared vectors (also checked by contracts/test/Vectors.t.sol) -------------------------------

@pytest.mark.parametrize("v", VECTORS["text_ids"], ids=lambda v: v["text"])
def test_vector_text_ids(v):
    assert to_hex(text_id(v["text"])) == v["id"]


@pytest.mark.parametrize("v", VECTORS["commitments"], ids=lambda v: v["batch_key"])
def test_vector_commitments(v):
    assert is_valid_lei(v["lei"])
    assert to_hex(buyer_id(v["lei"])) == v["buyer_id"]
    assert to_hex(text_id(v["batch_key"])) == v["batch_id"]
    got = commitment(from_hex(v["buyer_id"]), from_hex(v["salt"]), from_hex(v["batch_id"]), v["start"], v["end"])
    assert to_hex(got) == v["commitment"]


# --- shared with the browser (web/tests/parity.test.ts) -----------------------------------------

@pytest.mark.parametrize("v", VECTORS["lei_checks"], ids=lambda v: repr(v["lei"]))
def test_vector_lei_checks(v):
    assert is_valid_lei(v["lei"]) is v["valid"]


@pytest.mark.parametrize("v", VECTORS["buyer_ids"], ids=lambda v: repr(v["input"]))
def test_vector_buyer_id_normalises_input(v):
    assert to_hex(buyer_id(v["input"])) == v["buyer_id"]


@pytest.mark.parametrize("v", VECTORS["receipts"], ids=lambda v: v["name"])
def test_vector_receipts(v):
    from core.privacy.receipt import receipt_commitment
    if v["error"]:
        with pytest.raises(ValueError):
            receipt_commitment(v["receipt"])
    else:
        assert receipt_commitment(v["receipt"]) == v["commitment"]


@pytest.mark.parametrize("v", VECTORS["canonical_json"], ids=lambda v: v["hash"][:10])
def test_vector_canonical_json(v):
    from core.hashing import canonical_json, hash_json
    obj = json.loads(v["text"])
    assert canonical_json(obj).decode("utf-8") == v["canonical"] and hash_json(obj) == v["hash"]


# --- commitment ---------------------------------------------------------------------------------

def test_commitment_binds_every_field():
    b, s = buyer_id(fictional_lei(random.Random(3))), new_salt()
    base = commitment(b, s, BATCH, 100, 199)
    assert base != commitment(b, new_salt(), BATCH, 100, 199)
    assert base != commitment(b, s, text_id("other"), 100, 199)
    assert base != commitment(b, s, BATCH, 100, 200)
    assert base != commitment(b, s, BATCH, 101, 199)


def test_commitment_rejects_bad_inputs():
    b, s = buyer_id(fictional_lei(random.Random(4))), new_salt()
    with pytest.raises(ValueError):
        commitment(b, s, BATCH, 10, 5)
    with pytest.raises(ValueError):
        commitment(b, s[:31], BATCH, 1, 2)


# --- vault and audit ----------------------------------------------------------------------------

def make_retirement(lei=None, start=100, end=199):
    lei = lei or fictional_lei(random.Random(5))
    salt = new_salt()
    payload = VaultPayload(batch_id=to_hex(BATCH), start=start, end=end, lei=lei,
                           buyer_id=to_hex(buyer_id(lei)), salt=to_hex(salt))
    onchain = {"batchId": to_hex(BATCH), "start": start, "end": end,
               "buyerCommitment": to_hex(commitment(buyer_id(lei), salt, BATCH, start, end))}
    return payload, onchain


def test_vault_roundtrip_and_audit_passes():
    pub, priv = generate_keypair()
    payload, onchain = make_retirement()
    ct = seal(payload, pub)
    onchain["auditVaultHash"] = to_hex(vault_hash(ct))
    assert open_vault(ct, priv) == payload
    result = audit(ct, onchain, priv)
    assert result.valid, result.checks


def test_sealed_box_ciphertexts_differ_for_same_payload():
    pub, _ = generate_keypair()
    payload, _ = make_retirement()
    assert seal(payload, pub) != seal(payload, pub)


def test_audit_detects_tampered_ciphertext():
    pub, priv = generate_keypair()
    payload, onchain = make_retirement()
    ct = seal(payload, pub)
    onchain["auditVaultHash"] = to_hex(vault_hash(ct))
    tampered = ct[:-1] + bytes([ct[-1] ^ 1])
    result = audit(tampered, onchain, priv)
    assert not result.valid
    assert result.checks["vault_hash_matches_chain"] is False
    assert result.checks["vault_opens"] is False


def test_audit_detects_vault_for_wrong_buyer():
    pub, priv = generate_keypair()
    payload, onchain = make_retirement()
    other = VaultPayload(**{**payload.__dict__, "lei": fictional_lei(random.Random(6))})
    other = VaultPayload(**{**other.__dict__, "buyer_id": to_hex(buyer_id(other.lei))})
    ct = seal(other, pub)
    onchain["auditVaultHash"] = to_hex(vault_hash(ct))
    result = audit(ct, onchain, priv)
    assert not result.valid and result.checks["commitment_matches_chain"] is False


def test_audit_detects_range_mismatch():
    pub, priv = generate_keypair()
    payload, onchain = make_retirement()
    ct = seal(payload, pub)
    onchain.update(auditVaultHash=to_hex(vault_hash(ct)), end=250)
    result = audit(ct, onchain, priv)
    assert not result.valid and result.checks["range_matches_chain"] is False


def test_wrong_auditor_key_cannot_open():
    pub, _ = generate_keypair()
    _, other_priv = generate_keypair()
    payload, onchain = make_retirement()
    ct = seal(payload, pub)
    onchain["auditVaultHash"] = to_hex(vault_hash(ct))
    result = audit(ct, onchain, other_priv)
    assert not result.valid and result.checks["vault_opens"] is False


def test_vault_store(tmp_path):
    pub, _ = generate_keypair()
    payload, _ = make_retirement()
    store = VaultStore(tmp_path / "vault.sqlite")
    ct = seal(payload, pub)
    h = store.put(ct)
    assert h == to_hex(vault_hash(ct)) and store.get(h) == ct
    store.link(h, chain_id=31337, contract="0xABC", retirement_id=7)
    assert store.get_by_retirement(31337, "0xabc", 7) == ct
    with pytest.raises(KeyError):
        store.link("0x" + "00" * 32, 31337, "0xabc", 8)


# --- receipt ------------------------------------------------------------------------------------

def test_receipt_recomputes_onchain_commitment():
    lei, salt = fictional_lei(random.Random(7)), new_salt()
    r = build_receipt(retirement_id=1, chain_id=11155111, contract="0x0", tx_hash="0x1", batch_id=BATCH,
                      batch_key="VCS1477|batch-1", start=100, end=199, lei=lei, salt=salt)
    assert receipt_commitment(r) == to_hex(commitment(buyer_id(lei), salt, BATCH, 100, 199))
    assert "private" in r["warning"]
    with pytest.raises(ValueError):
        receipt_commitment({**r, "buyer_id": to_hex(text_id("someone else"))})
