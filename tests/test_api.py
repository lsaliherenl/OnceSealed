"""API tests against a throwaway Anvil chain. Skipped if anvil is not installed."""

import random

import pytest
from eth_account import Account
from fastapi.testclient import TestClient

from api.app import create_app
from core.chain import anvil
from core.chain.registry import Registry, connect
from core.config import ROLES, ChainSettings
from core.data.batches import load_batches
from core.privacy.commitment import new_salt, to_hex
from core.privacy.identity import fictional_lei
from core.privacy.vault import VaultStore, generate_keypair
from core.service import OnceSealed

pytestmark = pytest.mark.skipif(anvil.anvil_binary() is None, reason="anvil not installed")

TOKENS = {"operator": "op-token", "auditor": "aud-token"}
OP = {"X-Role-Token": "op-token"}
AUD = {"X-Role-Token": "aud-token"}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    port = anvil.free_port()
    proc = anvil.start_anvil(port)
    try:
        keys = {role: "0x" + Account.create().key.hex().removeprefix("0x") for role in ROLES}
        w3, accounts = connect(ChainSettings("anvil", f"http://127.0.0.1:{port}", keys))
        anvil.fund(w3, [a.address for a in accounts.values()])
        registry, _ = Registry.deploy(w3, accounts)
        pub, priv = generate_keypair()
        service = OnceSealed(registry, VaultStore(tmp_path_factory.mktemp("vault") / "v.sqlite"), pub, priv)
        yield TestClient(create_app(service, "anvil", TOKENS))
    finally:
        proc.terminate()


BATCH = next(b for b in load_batches("VCS1477") if b.vintage == 2020)
LEI_A, LEI_B = (fictional_lei(random.Random(9)) for _ in range(2))


def test_health_and_config(client):
    assert client.get("/api/health").json()["ok"]
    cfg = client.get("/api/config").json()
    assert cfg["chain_id"] == 31337 and cfg["contract"].startswith("0x")


def test_projects_and_report_anchoring(client):
    projects = client.get("/api/projects").json()
    assert {"VCS1477", "VCS1851"} <= {p["project_id"] for p in projects}
    detail = client.get("/api/projects/VCS1477").json()
    assert detail["report"]["project"]["project_id"] == "VCS1477" and detail["onchain"] is None

    assert client.post("/api/reports/VCS1477/anchor").status_code == 401
    res = client.post("/api/reports/VCS1477/anchor", headers=OP).json()
    assert res["version"] == 1 and res["report_hash"] == detail["report_hash"]
    onchain = client.get("/api/projects/VCS1477").json()["onchain"]
    assert onchain["matches_published_file"] and onchain["version"] == 1


def test_retire_overlap_audit_and_disclosure(client):
    body = {"batch_key": BATCH.key, "start": 1, "end": 500, "lei": LEI_A}
    assert client.post("/api/retirements", json=body).status_code == 401
    r = client.post("/api/retirements", json=body, headers=OP)
    assert r.status_code == 200, r.text
    out = r.json()
    rid, receipt = out["retirement"]["retirement_id"], out["receipt"]
    assert out["retirement"]["audit_status"] == "pending"
    assert "lei" not in out["retirement"] and receipt["lei"] == LEI_A

    clash = client.post("/api/retirements", json={**body, "start": 400, "end": 900, "lei": LEI_B}, headers=OP)
    assert clash.status_code == 409
    assert clash.json()["error"] == "AlreadyRetired" and clash.json()["args"]["conflictingRetirementId"] == rid

    bad = client.post("/api/retirements", json={**body, "start": 600, "end": 700, "lei": "NOTALEI"}, headers=OP)
    assert bad.status_code == 400

    look = client.get("/api/lookup", params={"batch_key": BATCH.key, "serial": 250}).json()
    assert look["retired"] and look["retirement"]["retirement_id"] == rid
    batches = {b["key"]: b for b in client.get("/api/projects/VCS1477/batches").json()}
    assert batches[BATCH.key]["retired_quantity"] == 500

    assert client.get("/api/audit/pending").status_code == 401
    assert rid in [p["retirement_id"] for p in client.get("/api/audit/pending", headers=AUD).json()]
    opened = client.post(f"/api/audit/{rid}/open", headers=AUD).json()
    assert opened["valid"] and opened["vault"]["lei"] == LEI_A and all(opened["checks"].values())
    assert client.post(f"/api/audit/{rid}/open", headers=OP).status_code == 401
    attested = client.post(f"/api/audit/{rid}/attest", json={"valid": True}, headers=AUD).json()
    assert attested["retirement"]["audit_status"] == "verified"
    again = client.post(f"/api/audit/{rid}/attest", json={"valid": False}, headers=AUD)
    assert again.status_code == 409 and again.json()["error"] == "AlreadyAttested"

    ok = client.post("/api/receipts/verify", json=receipt).json()
    assert ok["valid"] and ok["audit_status"] == "verified"
    forged = client.post("/api/receipts/verify", json={**receipt, "salt": to_hex(new_salt())}).json()
    assert not forged["valid"]
