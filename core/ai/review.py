"""Human review of the checks the two models disagree on.

A check whose second opinion disagrees with the LLM is flagged ``needs_review``. A team member reads the excerpt
and records a decision in reviews/<project>.json (published with the reports). When the report is built again the
decision is applied: a "found" or "not found" decision replaces the model's answer in the principle's status and
score, while the model's answer stays in the report next to it; "unclear" keeps the model's answer and the flag.

A decision is tied to the documents it was made on (``document_sha256``): if the project's documents change, the
excerpt changes too, and the decision is not applied until a person looks again.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT

REVIEWS = PROJECT_ROOT / "reviews"
REVIEW_SCHEMA = "review-v1"
REVIEW_RULE = "person-decides-flagged-checks-v1"
DECISIONS = {"found": "yes", "not_found": "no", "unclear": None}


def review_path(project_id: str) -> Path:
    return REVIEWS / f"{project_id}.json"


def load(project_id: str) -> dict[str, Any]:
    p = review_path(project_id)
    if not p.exists():
        return {"schema": REVIEW_SCHEMA, "project_id": project_id, "decisions": []}
    return json.loads(p.read_text(encoding="utf-8"))


def record(project_id: str, document_sha256: str, principle: str, check_id: str, decision: str, note: str,
           model_answer: str | None) -> dict[str, Any]:
    """Add or replace the decision on one check; returns the stored entry."""
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {list(DECISIONS)}")
    data = load(project_id)
    entry = {"principle": principle, "check_id": check_id, "decision": decision, "note": note.strip()[:1000],
             "model_answer": model_answer, "document_sha256": document_sha256, "reviewer": "team member",
             "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    data["decisions"] = [d for d in data["decisions"]
                         if not (d["principle"] == principle and d["check_id"] == check_id)] + [entry]
    data["decisions"].sort(key=lambda d: (d["principle"], d["check_id"]))
    path = review_path(project_id)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return entry


def decisions_for(project_id: str, document_sha256: str) -> dict[tuple[str, str], dict[str, Any]]:
    """The decisions made on these exact documents, by (principle, check id)."""
    return {(d["principle"], d["check_id"]): d for d in load(project_id)["decisions"]
            if d["document_sha256"] == document_sha256}


def final_answer(check: dict[str, Any]) -> str | None:
    """The answer that counts: the person's decision when there is one, else the model's."""
    review = check.get("human_review")
    if review and DECISIONS.get(review["decision"]) is not None:
        return DECISIONS[review["decision"]]
    return check["answer"]
