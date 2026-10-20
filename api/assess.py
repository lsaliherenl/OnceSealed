"""Assessor routes: register a document, run the quality assessment, compare the draft, publish and anchor it.

The assessment is the same code the published reports come from (core.ai.assessment). It runs in a background
thread because it can take minutes (two models, five principles); the result is kept as a draft in
data/drafts/<project>.json until the assessor publishes it. On Sepolia publishing anchors it, writes
reports/<project>.json and its archived version, logs the transaction and refreshes the web data; on a local chain
it is only anchored there, so the published files keep mirroring Sepolia. Local demo only, like the operator and
auditor routes.
"""

import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from core.ai import assessment, review
from core.ai.checklist_models import JevChecklist, LLMChecklist
from core.ai.principles import PRINCIPLES
from core.ai.sources import ROLES, get_project, register_document
from core.config import PROJECT_ROOT
from core.reports import archive, log_anchor
from core.service import OnceSealed

DRAFTS = PROJECT_ROOT / "data" / "drafts"
MAX_PDF_BYTES = 80 * 1024 * 1024
SEPOLIA = 11155111


class RunRequest(BaseModel):
    use_cache: bool = True
    second_opinion: bool = True


class ReviewRequest(BaseModel):
    principle: str
    check_id: str
    decision: str
    note: str = ""


def _manifest_entry(pid: str) -> dict[str, Any]:
    docs = json.loads((PROJECT_ROOT / "samples" / "manifest.json").read_text(encoding="utf-8"))["documents"]
    entry = next((d for d in docs if d["project_id"] == pid), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"{pid} is not in samples/manifest.json")
    return entry


def _published(pid: str) -> dict[str, Any] | None:
    p = PROJECT_ROOT / "reports" / f"{pid}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _draft_path(pid: str) -> Path:
    return DRAFTS / f"{pid}.json"


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    return {"overall": report["overall"]["score"], "generated_at": report["generated_at"],
            "method_hash": report["method_hash"],
            "principles": [{"principle": p["principle"], "status": p["status"], "score": p["score"],
                            "review_flags": p["review_flags"]} for p in report["principles"]],
            "documents": 1 + len(report["document"].get("extra_files", []))}


def compare(published: dict[str, Any] | None, draft: dict[str, Any]) -> dict[str, Any]:
    """What would change if the draft replaced the published report."""
    def answers(r: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
        return {} if r is None else {(p["principle"], c["id"]): c for p in r["principles"] for c in p["checks"]}

    old, new = answers(published), answers(draft)
    changed = [{"principle": k[0], "id": k[1], "question": new[k]["question"],
                "before": old[k]["answer"] if k in old else None, "after": new[k]["answer"],
                "evidence": new[k]["evidence"][:1]}
               for k in new if k not in old or old[k]["answer"] != new[k]["answer"]]
    return {"published": _summary(published) if published else None, "draft": _summary(draft),
            "changed_checks": changed, "unchanged_checks": len(new) - len(changed),
            "same_method": bool(published) and published["method_hash"] == draft["method_hash"]}


class Jobs:
    """One assessment at a time per project; state in memory, the result on disk."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.state: dict[str, dict[str, Any]] = {}

    def get(self, pid: str) -> dict[str, Any] | None:
        with self.lock:
            return dict(self.state[pid]) if pid in self.state else None

    def start(self, pid: str, work: Callable[[Callable[[str], None]], None]) -> None:
        with self.lock:
            if self.state.get(pid, {}).get("status") == "running":
                raise HTTPException(status_code=409, detail="an assessment of this project is already running")
            self.state[pid] = {"status": "running", "done": [], "total": len(PRINCIPLES), "error": None,
                               "started_at": time.time()}

        def progress(key: str) -> None:
            with self.lock:
                self.state[pid]["done"].append(key)

        def target() -> None:
            try:
                work(progress)
                status, error = "done", None
            except Exception as e:  # reported to the screen; the published report is untouched
                status, error = "failed", f"{e.__class__.__name__}: {e}"
            with self.lock:
                self.state[pid].update(status=status, error=error, finished_at=time.time())

        threading.Thread(target=target, daemon=True).start()


def add_assessor_routes(app: FastAPI, service: OnceSealed, require: Callable[[str], Any]) -> None:
    jobs = Jobs()
    guard = [Depends(require("assessor"))]

    @app.get("/api/assess/projects", dependencies=guard)
    def projects() -> list[dict[str, Any]]:
        out = []
        docs = json.loads((PROJECT_ROOT / "samples" / "manifest.json").read_text(encoding="utf-8"))["documents"]
        for d in docs:
            pid = d["project_id"]
            src = get_project(pid)
            published = _published(pid)
            out.append({
                "project_id": pid, "name": d["project_name"],
                "documents": [{"role": f.role, "covers": list(f.covers), "file_name": f.file_name, "period": f.period,
                               "status": f.status()} for f in src.files],
                "missing_roles": src.coverage()["missing"],
                "published": _summary(published) if published else None,
                "draft": _draft_path(pid).exists(),
                "job": jobs.get(pid),
            })
        return out

    @app.post("/api/assess/{pid}/documents", dependencies=guard)
    async def upload(pid: str, request: Request, role: str, file_name: str, period: str | None = None,
                     url: str | None = None) -> dict[str, Any]:
        _manifest_entry(pid)
        body = await request.body()
        if not body.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="not a PDF file")
        if len(body) > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="PDF larger than 80 MB")
        if role not in ROLES:
            raise HTTPException(status_code=400, detail=f"unknown role {role}")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upload.pdf"
            path.write_bytes(body)
            record = register_document(pid, role, path, file_name=Path(file_name).name, url=url, period=period or None)
        return {"record": record, "missing_roles": get_project(pid).coverage()["missing"]}

    @app.post("/api/assess/{pid}/run", dependencies=guard)
    def start(pid: str, req: RunRequest) -> dict[str, Any]:
        entry = _manifest_entry(pid)
        missing = [f.file_name for f in get_project(pid).files if f.status() != "present"]
        if missing:
            raise HTTPException(status_code=409, detail=f"documents not available on this machine: {missing}")

        def work(progress: Callable[[str], None]) -> None:
            second = JevChecklist() if req.second_opinion else None
            a = assessment.run(entry, LLMChecklist(), second, None, req.use_cache, progress)
            DRAFTS.mkdir(parents=True, exist_ok=True)
            _draft_path(pid).write_text(json.dumps({"report": a.report, "run_log": a.run_log, "evidence": a.evidence,
                                                    "cost": a.cost}, ensure_ascii=False, default=str),
                                        encoding="utf-8")

        jobs.start(pid, work)
        return {"status": "running"}

    @app.get("/api/assess/{pid}/draft", dependencies=guard)
    def draft(pid: str) -> dict[str, Any]:
        job = jobs.get(pid)
        path = _draft_path(pid)
        if not path.exists():
            return {"job": job, "draft": None}
        d = json.loads(path.read_text(encoding="utf-8"))
        return {"job": job, "draft": {"cost": d["cost"], "report_hash": assessment.report_hash(d["report"]),
                                      **compare(_published(pid), d["report"])}}

    @app.post("/api/assess/{pid}/discard", dependencies=guard)
    def discard(pid: str) -> dict[str, Any]:
        _draft_path(pid).unlink(missing_ok=True)
        return {"discarded": True}

    @app.post("/api/assess/{pid}/publish", dependencies=guard)
    def publish(pid: str) -> dict[str, Any]:
        path = _draft_path(pid)
        if not path.exists():
            raise HTTPException(status_code=404, detail="no draft to publish; run an assessment first")
        d = json.loads(path.read_text(encoding="utf-8"))
        a = assessment.Assessment(d["report"], d["run_log"], d["evidence"])
        if a.report["overall"]["score"] is None:
            raise HTTPException(status_code=400, detail="the draft has no overall score; nothing to anchor")
        version, tx, rhash = service.publish_report(a.report)
        path.unlink()
        out = {"version": version, "report_hash": rhash, "tx_hash": tx.tx_hash, "gas_used": tx.gas_used,
               "chain_id": service.chain_id, "files_written": False, "web_data_refreshed": False, "export_error": None}
        if service.chain_id != SEPOLIA:
            return out  # a local chain: anchored there only; the published files keep mirroring Sepolia
        assessment.save(pid, a)
        archive(pid, version)
        log_anchor(service.registry.address, tx.tx_hash, tx.block_number, tx.gas_used, pid, version, rhash)
        export = subprocess.run([sys.executable, "scripts/export_web_data.py"], cwd=PROJECT_ROOT,
                                capture_output=True, text=True)
        return {**out, "files_written": True, "web_data_refreshed": export.returncode == 0,
                "export_error": export.stderr[-400:] if export.returncode else None}

    # --- human review of flagged checks ------------------------------------------------------

    @app.get("/api/review/queue", dependencies=guard)
    def queue() -> list[dict[str, Any]]:
        """Checks the models disagree on in the published reports, with any decision already made."""
        out = []
        docs = json.loads((PROJECT_ROOT / "samples" / "manifest.json").read_text(encoding="utf-8"))["documents"]
        for d in docs:
            pid = d["project_id"]
            report = _published(pid)
            if report is None:
                continue
            sha = report["document"]["sha256"]
            decisions = review.decisions_for(pid, sha)
            for p in report["principles"]:
                for c in p["checks"]:
                    decision = decisions.get((p["principle"], c["id"]))
                    if not (c["needs_review"] or c.get("human_review") or decision):
                        continue
                    out.append({"project_id": pid, "name": d["project_name"], "principle": p["principle"],
                                "check_id": c["id"], "question": c["question"], "answer": c["answer"],
                                "evidence": c["evidence"], "second_opinion_p_yes": c["second_opinion_p_yes"],
                                "decision": decision, "in_published_report": bool(c.get("human_review"))})
        return out

    @app.get("/api/review/{pid}/{principle}/excerpt", dependencies=guard)
    def excerpt(pid: str, principle: str) -> dict[str, Any]:
        """The paragraphs the models read for this principle (data/evidence/<pid>.jsonl)."""
        path = PROJECT_ROOT / "data" / "evidence" / f"{pid}.jsonl"
        if not path.exists():
            raise HTTPException(status_code=404, detail="no evidence file; run the assessment first")
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["principle"] == principle:
                return {"paragraphs": row["paragraphs"], "document_sha256": row["document_sha256"]}
        raise HTTPException(status_code=404, detail=f"no excerpt for {principle}")

    @app.post("/api/review/{pid}", dependencies=guard)
    def decide(pid: str, req: ReviewRequest) -> dict[str, Any]:
        report = _published(pid)
        if report is None:
            raise HTTPException(status_code=404, detail="no published report")
        check = next((c for p in report["principles"] if p["principle"] == req.principle
                      for c in p["checks"] if c["id"] == req.check_id), None)
        if check is None:
            raise HTTPException(status_code=404, detail="no such check in the published report")
        entry = review.record(pid, report["document"]["sha256"], req.principle, req.check_id, req.decision,
                              req.note, check["answer"])
        return {"decision": entry}

