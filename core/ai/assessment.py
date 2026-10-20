"""Run the quality assessment of one manifest project and write its outputs.

Shared by scripts/assess_project.py and the API's assessor screen (api/assess.py), so a report produced from the
web app is made by exactly the same code as the published ones. ``run`` reads and judges; ``save`` publishes:

    reports/<project_id>.json                   published report (its keccak256 goes on-chain)
    data/runs/reports/<project_id>-<ts>.json    run log (costs, served models)
    data/evidence/<project_id>.jsonl            excerpts + checklist questions, for evaluating other decision models
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.ai import review
from core.ai.checklist import BY_PRINCIPLE, QUESTION_SET_VERSION
from core.ai.checklist_models import JevChecklist, LLMChecklist
from core.ai.pdf_extract import extract_many, file_sha256
from core.ai.report import build_report, report_hash
from core.config import PROJECT_ROOT

CACHE = PROJECT_ROOT / "data" / "cache" / "checklist"


@dataclass
class Assessment:
    report: dict[str, Any]
    run_log: dict[str, Any]
    evidence: list[dict[str, Any]]  # one line per principle: the excerpt read and the questions asked

    @property
    def report_hash(self) -> str:
        return report_hash(self.report)

    @property
    def cost(self) -> float:
        return (sum(x["cost"] or 0 for x in self.run_log["llm"])
                + sum(x.get("cost") or 0 for x in self.run_log["second_opinion"]))


def run(project: dict[str, Any], llm: LLMChecklist, second: JevChecklist | None,
        principles: list[str] | None = None, use_cache: bool = True,
        on_principle: Callable[[str], None] | None = None) -> Assessment:
    """Assess the project's documents as listed in the manifest; nothing is written."""
    pid = project["project_id"]
    files = [project] + project.get("extra_files", [])
    for f in files:
        if f.get("sha256") and f["sha256"] != file_sha256(PROJECT_ROOT / f["local_path"]):
            raise ValueError(f"{f['local_path']} does not match the sha256 recorded in the manifest")
    doc = extract_many(PROJECT_ROOT / project["local_path"], [PROJECT_ROOT / f["local_path"] for f in files[1:]])
    reviews = review.decisions_for(pid, doc.sha256)  # a person's decisions on flagged checks, same documents only
    report, run_log = build_report(doc, project, llm, second, principles, CACHE if use_cache else None, on_principle,
                                   reviews)

    by_id = {p.id: p for p in doc.paragraphs}
    evidence = [{
        "project_id": pid, "document_sha256": doc.sha256, "principle": p["principle"],
        "question_set_version": QUESTION_SET_VERSION,
        "questions": [{"id": q.id, "text": q.text} for q in BY_PRINCIPLE[p["principle"]]],
        "paragraphs": [{"id": i, "page": by_id[i].page, "text": by_id[i].text} for i in p["excerpt"]["paragraphs"]],
    } for p in report["principles"] if p["checks"]]
    return Assessment(report, run_log, evidence)


def save(project_id: str, a: Assessment) -> Path:
    """Publish the assessment: the report file, its run log and the evidence excerpts."""
    out = PROJECT_ROOT / "reports" / f"{project_id}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(a.report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log_dir = PROJECT_ROOT / "data" / "runs" / "reports"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{project_id}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps({"report_hash": a.report_hash, **a.run_log}, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    ev_dir = PROJECT_ROOT / "data" / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    with open(ev_dir / f"{project_id}.jsonl", "w", encoding="utf-8") as f:
        for line in a.evidence:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return out
