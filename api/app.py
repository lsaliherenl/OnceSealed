"""FastAPI app: wraps core.service.OnceSealed for the web UI.

Public endpoints (no token) only read public data. Writing as the registry operator and
anything that reveals a buyer's identity (the auditor's vault) needs a role token sent as
`X-Role-Token`. In this prototype the server holds the operator and auditor keys; in a real
deployment each party would sign with its own key.

Note: the public verification page does not need this server at all; the browser reads the
contract directly. The `/api/receipts/verify` endpoint is a convenience mirror of that check.
"""

import json
import secrets
from dataclasses import asdict
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.chain.registry import RegistryError, Retirement, load_artifact
from core.config import PROJECT_ROOT
from core.data.batches import IssuanceBatch, load_batches
from core.hashing import hash_json
from core.privacy.commitment import to_hex
from core.privacy.identity import is_valid_lei, project_id as project_id_bytes
from core.service import OnceSealed

EXPLORERS = {11155111: "https://sepolia.etherscan.io"}


class RetireRequest(BaseModel):
    batch_key: str
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    lei: str


class AttestRequest(BaseModel):
    valid: bool


@lru_cache(maxsize=1)
def _manifest() -> list[dict[str, Any]]:
    return json.loads((PROJECT_ROOT / "samples" / "manifest.json").read_text(encoding="utf-8"))["documents"]


@lru_cache(maxsize=1)
def _batches_by_key() -> dict[str, IssuanceBatch]:
    return {b.key: b for b in load_batches()}


@lru_cache(maxsize=1)
def _batches_by_id() -> dict[bytes, IssuanceBatch]:
    return {b.batch_id: b for b in load_batches()}


def _report(project_id: str) -> dict[str, Any] | None:
    p = PROJECT_ROOT / "reports" / f"{project_id}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _public(r: Retirement) -> dict[str, Any]:
    batch = _batches_by_id().get(r.batch_id)
    return {
        "retirement_id": r.retirement_id,
        "batch_id": to_hex(r.batch_id),
        "batch_key": batch.key if batch else None,
        "project_id": batch.project_id if batch else None,
        "start": r.start,
        "end": r.end,
        "quantity": r.end - r.start + 1,
        "serial_label": batch.serial_label(r.start, r.end) if batch else None,
        "buyer_commitment": to_hex(r.buyer_commitment),
        "audit_vault_hash": to_hex(r.audit_vault_hash),
        "report_version": r.report_version,
        "retired_at": _iso(r.retired_at),
        "audit_status": r.audit.name.lower(),
    }


def create_app(service: OnceSealed, network: str, tokens: dict[str, str],
               cors_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(title="OnceSealed API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins or ["http://localhost:3000"],
                       allow_methods=["*"], allow_headers=["*"])
    reg = service.registry

    def require(role: str):
        def check(x_role_token: str = Header(default="")) -> None:
            expected = tokens.get(role, "")
            if not expected or not secrets.compare_digest(x_role_token, expected):
                raise HTTPException(status_code=401, detail=f"{role} token required")
        return check

    @app.exception_handler(RegistryError)
    async def registry_error(_: Request, e: RegistryError) -> JSONResponse:
        args = {k: (to_hex(v) if isinstance(v, bytes) else v) for k, v in e.args_dict.items()}
        return JSONResponse(status_code=409, content={"error": e.name, "args": args, "message": str(e)})

    @app.exception_handler(ValueError)
    async def value_error(_: Request, e: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": "InvalidInput", "message": str(e)})

    # --- public ----------------------------------------------------------------------------

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "network": network, "chain_id": service.chain_id}

    @app.get("/api/config")
    def config() -> dict[str, Any]:
        return {"network": network, "chain_id": service.chain_id, "contract": reg.address,
                "explorer": EXPLORERS.get(service.chain_id), "compiler": load_artifact()["compiler"]}

    @app.get("/api/abi")
    def abi() -> list[dict[str, Any]]:
        return load_artifact()["abi"]

    @app.get("/api/buyers")
    def buyers() -> list[dict[str, Any]]:
        return json.loads((PROJECT_ROOT / "data" / "demo_buyers.json").read_text(encoding="utf-8"))["buyers"]

    def _onchain_report(pid: str, report: dict[str, Any] | None) -> dict[str, Any] | None:
        count = reg.report_count(project_id_bytes(pid))
        if count == 0:
            return None
        latest = reg.get_report(project_id_bytes(pid), count)
        return {"version": count, "report_hash": to_hex(latest.report_hash), "method_hash": to_hex(latest.method_hash),
                "score": latest.score, "registered_at": _iso(latest.registered_at),
                "matches_published_file": bool(report) and to_hex(latest.report_hash) == hash_json(report)}

    @app.get("/api/projects")
    def projects() -> list[dict[str, Any]]:
        out = []
        for d in _manifest():
            report = _report(d["project_id"])
            out.append({
                "project_id": d["project_id"], "name": d["project_name"], "category": d["category"],
                "registry_url": d["registry_url"], "methodology": d["methodology"],
                "has_report": report is not None,
                "overall_score": report["overall"]["score"] if report else None,
                "methodology_status": report["methodology_status"]["status"] if report else None,
            })
        return out

    @app.get("/api/projects/{pid}")
    def project(pid: str) -> dict[str, Any]:
        d = next((x for x in _manifest() if x["project_id"] == pid), None)
        if d is None:
            raise HTTPException(status_code=404, detail="unknown project")
        report = _report(pid)
        return {"project": d, "report": report, "report_hash": hash_json(report) if report else None,
                "onchain": _onchain_report(pid, report)}

    @app.get("/api/projects/{pid}/batches")
    def batches(pid: str) -> list[dict[str, Any]]:
        out = []
        for b in load_batches(pid):
            registered = reg.batch_exists(b.batch_id)
            ids = reg.batch_retirements(b.batch_id) if registered else []
            retired = sum(r.end - r.start + 1 for r in (reg.get_retirement(i) for i in ids))
            out.append({"key": b.key, "batch_id": to_hex(b.batch_id), "vintage": b.vintage, "batch_no": b.batch_no,
                        "first_serial": b.first_serial, "last_serial": b.last_serial, "quantity": b.quantity,
                        "registered": registered, "retirements": len(ids), "retired_quantity": retired})
        return out

    @app.get("/api/retirements")
    def retirements(project_id: str | None = None) -> list[dict[str, Any]]:
        out = [_public(reg.get_retirement(i)) for i in range(1, reg.retirement_count() + 1)]
        return [r for r in out if project_id is None or r["project_id"] == project_id]

    @app.get("/api/retirements/{rid}")
    def retirement(rid: int) -> dict[str, Any]:
        return _public(reg.get_retirement(rid))

    @app.get("/api/lookup")
    def lookup(batch_key: str, serial: int) -> dict[str, Any]:
        b = _batches_by_key().get(batch_key)
        if b is None:
            raise HTTPException(status_code=404, detail="unknown batch")
        rid = reg.retirement_of(b.batch_id, serial) if reg.batch_exists(b.batch_id) else 0
        return {"batch_key": batch_key, "serial": serial, "retired": rid != 0,
                "retirement": _public(reg.get_retirement(rid)) if rid else None}

    @app.post("/api/receipts/verify")
    def verify_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
        check = service.verify_receipt(receipt)
        return {"valid": check.valid, "checks": check.checks,
                "audit_status": check.audit_status.name.lower() if check.audit_status is not None else None,
                "error": check.error}

    # --- registry operator -----------------------------------------------------------------

    @app.post("/api/reports/{pid}/anchor", dependencies=[Depends(require("operator"))])
    def anchor_report(pid: str) -> dict[str, Any]:
        report = _report(pid)
        if report is None:
            raise HTTPException(status_code=404, detail="no published report")
        version, tx, rhash = service.publish_report(report)
        return {"version": version, "report_hash": rhash, "tx_hash": tx.tx_hash, "gas_used": tx.gas_used}

    @app.post("/api/retirements", dependencies=[Depends(require("operator"))])
    def retire(req: RetireRequest) -> dict[str, Any]:
        batch = _batches_by_key().get(req.batch_key)
        if batch is None:
            raise HTTPException(status_code=404, detail="unknown batch")
        lei = req.lei.strip().upper()
        if not is_valid_lei(lei):
            raise ValueError("invalid LEI")
        service.ensure_batch(batch)
        out = service.retire(batch, req.start, req.end, lei)
        # The receipt (with the salt) is returned once and never stored in plain text on the server.
        return {"retirement": _public(reg.get_retirement(out.retirement_id)), "tx_hash": out.tx.tx_hash,
                "gas_used": out.tx.gas_used, "receipt": out.receipt}

    # --- auditor ---------------------------------------------------------------------------

    @app.get("/api/audit/pending", dependencies=[Depends(require("auditor"))])
    def pending() -> list[dict[str, Any]]:
        return [r for r in retirements() if r["audit_status"] == "pending"]

    @app.post("/api/audit/{rid}/open", dependencies=[Depends(require("auditor"))])
    def open_vault(rid: int) -> dict[str, Any]:
        result, _ = service.audit(rid, attest=False)
        return {"valid": result.valid, "checks": result.checks, "error": result.error,
                "vault": asdict(result.payload) if result.payload else None,
                "retirement": _public(reg.get_retirement(rid))}

    @app.post("/api/audit/{rid}/attest", dependencies=[Depends(require("auditor"))])
    def attest(rid: int, req: AttestRequest) -> dict[str, Any]:
        tx = reg.attest(rid, req.valid)
        return {"retirement": _public(reg.get_retirement(rid)), "tx_hash": tx.tx_hash}

    return app
