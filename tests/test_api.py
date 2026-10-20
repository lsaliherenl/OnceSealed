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

TOKENS = {"operator": "op-token", "auditor": "aud-token", "assessor": "as-token"}
OP = {"X-Role-Token": "op-token"}
AUD = {"X-Role-Token": "aud-token"}
AS = {"X-Role-Token": "as-token"}


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
    assert BATCH.lot_size == 1000
    body = {"batch_key": BATCH.key, "start": 1, "end": 2000, "lei": LEI_A}
    assert client.post("/api/retirements", json=body).status_code == 401
    r = client.post("/api/retirements", json=body, headers=OP)
    assert r.status_code == 200, r.text
    out = r.json()
    lots, bundle = out["retirements"], out["receipt"]
    assert [(x["start"], x["end"]) for x in lots] == [(1, 1000), (1001, 2000)]  # one retirement per lot
    assert all(x["audit_status"] == "pending" and "lei" not in x for x in lots)
    assert bundle["lei"] == LEI_A and bundle["quantity"] == 2000 and len(bundle["lots"]) == 2
    rid, receipt = lots[0]["retirement_id"], bundle["lots"][0]
    assert receipt["salt"] != bundle["lots"][1]["salt"]  # lots cannot be linked through a shared salt

    clash = client.post("/api/retirements", json={**body, "start": 1001, "end": 3000, "lei": LEI_B}, headers=OP)
    assert clash.status_code == 409
    assert clash.json()["error"] == "AlreadyRetired"
    assert clash.json()["args"]["conflictingRetirementId"] == lots[1]["retirement_id"]
    misaligned = client.post("/api/retirements", json={**body, "start": 2001, "end": 2500, "lei": LEI_B}, headers=OP)
    assert misaligned.status_code == 400 and "lot" in misaligned.text

    bad = client.post("/api/retirements", json={**body, "start": 3001, "end": 4000, "lei": "NOTALEI"}, headers=OP)
    assert bad.status_code == 400

    look = client.get("/api/lookup", params={"batch_key": BATCH.key, "serial": 250}).json()
    assert look["retired"] and look["retirement"]["retirement_id"] == rid
    batches = {b["key"]: b for b in client.get("/api/projects/VCS1477/batches").json()}
    assert batches[BATCH.key]["retired_quantity"] == 2000 and batches[BATCH.key]["lot_size"] == 1000

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
    # the bundle verifies as a whole, but stays pending until every lot is audited
    whole = client.post("/api/receipts/verify", json=bundle).json()
    assert whole["valid"] and whole["audit_status"] == "pending"


def test_assessor_runs_compares_and_publishes_a_draft(client, monkeypatch, tmp_path):
    """The assessment itself is stubbed (no model calls); the routes, draft, comparison and anchoring are real."""
    import copy
    import json
    import time

    from api import assess
    from core.ai.assessment import Assessment
    from core.config import PROJECT_ROOT

    published = json.loads((PROJECT_ROOT / "reports" / "VCS1851.json").read_text(encoding="utf-8"))
    report = copy.deepcopy(published)
    first = report["principles"][0]["checks"][0]
    first["answer"] = "no" if first["answer"] == "yes" else "yes"
    saved = {}

    def fake_run(project, llm, second, principles, use_cache, progress):
        for p in report["principles"]:
            progress(p["principle"])
        return Assessment(report, {"llm": [{"cost": 0.01}], "second_opinion": []}, [])

    monkeypatch.setattr(assess, "DRAFTS", tmp_path)
    monkeypatch.setattr(assess, "LLMChecklist", lambda: None)
    monkeypatch.setattr(assess, "JevChecklist", lambda: None)
    monkeypatch.setattr(assess.assessment, "run", fake_run)
    monkeypatch.setattr(assess.assessment, "save", lambda pid, a: saved.setdefault(pid, a))
    monkeypatch.setattr(assess.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 0, "stderr": ""})())
    monkeypatch.setattr(assess, "get_project", lambda pid: type("P", (), {"files": []})())

    assert client.post("/api/assess/VCS1851/run", json={}).status_code == 401
    assert client.post("/api/assess/VCS1851/run", json={}, headers=AS).json() == {"status": "running"}
    for _ in range(50):
        d = client.get("/api/assess/VCS1851/draft", headers=AS).json()
        if d["job"]["status"] != "running":
            break
        time.sleep(0.1)
    assert d["job"]["status"] == "done" and len(d["job"]["done"]) == len(report["principles"])
    draft = d["draft"]
    assert draft["cost"] == 0.01 and draft["same_method"]
    assert [(c["id"], c["before"], c["after"]) for c in draft["changed_checks"]] == [
        (first["id"], "no" if first["answer"] == "yes" else "yes", first["answer"])]

    res = client.post("/api/assess/VCS1851/publish", headers=AS).json()
    assert res["version"] >= 1 and res["report_hash"] == draft["report_hash"]
    assert not res["files_written"] and saved == {}  # a local chain never rewrites the published Sepolia files
    assert client.get("/api/assess/VCS1851/draft", headers=AS).json()["draft"] is None


def test_assessor_upload_rejects_non_pdf(client):
    res = client.post("/api/assess/VCS1851/documents?role=monitoring_report&file_name=x.pdf", content=b"hello",
                      headers=AS)
    assert res.status_code == 400
