"""Build the three-layer quality report for one project document.

Layer 1  methodology status   deterministic table lookup (core.ai.methodology)
Layer 2  evidence extraction  LLM quotes, each verified against the PDF text (core.ai.assess)
Layer 3  evidence judgement   decision model probabilities (core.ai.decision)

The report is published as JSON; its keccak256 over canonical JSON goes on-chain
together with ``method_hash``, which pins the models and question set used.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf

from core.ai.assess import PROMPT_VERSION, PrincipleResult, assess_principle
from core.ai.client import ChatClient
from core.ai.decision import QUESTION_SET_VERSION, Decision, DecisionError, DecisionModel
from core.ai.methodology import load_table, methodology_status
from core.ai.pdf_extract import Document
from core.ai.principles import BY_KEY, PRINCIPLES
from core.ai.quotes import QuoteVerifier
from core.hashing import hash_json

log = logging.getLogger(__name__)

REPORT_SCHEMA_VERSION = "report-v1"
DECISION_INPUT = "verified_quotes"  # what the decision model sees; see CLAUDE.md open question

DISCLAIMER = (
    "Signal, not verdict. Scores describe how well the submitted document evidences each ICVCM principle. "
    "They are not an ICVCM assessment, a rating of the project, or a statement about its real-world impact."
)


def _r(x: float) -> float:
    return round(float(x), 4)


def _decision_dict(d: Decision) -> dict[str, Any]:
    return {
        "evidence_level": d.evidence_level,
        "evidence_probabilities": {k: _r(v) for k, v in d.evidence_probabilities.items()},
        "evidence_confidence": _r(d.evidence_confidence),
        "independent_sources": _r(d.independent),
        "strength": _r(d.strength),
        "strength_probabilities": {k: _r(v) for k, v in d.strength_probabilities.items()},
        "strength_confidence": _r(d.strength_confidence),
        "model": d.model,
    }


def judge_principle(llm: PrincipleResult, decision_model: DecisionModel) -> dict[str, Any]:
    """Combine the LLM's verified evidence with the decision model's judgement."""
    entry: dict[str, Any] = {
        "principle": llm.principle,
        "rationale": llm.rationale,
        "quotes": [{"text": q.text, "page": q.page, "paragraph_id": q.paragraph_id, "verification": q.method}
                   for q in llm.quotes],
        "dropped_findings": llm.dropped_findings,
        "llm": {"status": llm.model_status, "score": llm.model_score, "model": llm.served_model},
        "decision": None,
    }
    if llm.status == "assessment_failed":
        return {**entry, "status": "assessment_failed", "score": None}
    if llm.status == "not_applicable":
        return {**entry, "status": "not_applicable", "score": None}
    if not llm.quotes:
        return {**entry, "status": "no_evidence", "score": 0}
    try:
        decision = decision_model.decide(BY_KEY[llm.principle], [q.text for q in llm.quotes])
    except DecisionError as e:
        log.warning("decision failed for %s: %s", llm.principle, e)
        return {**entry, "status": "assessment_failed", "score": None}
    review = ["decision_questions_disagree"] if decision.questions_disagree else []
    return {**entry, "status": decision.status, "score": decision.score, "review_flags": review,
            "decision": _decision_dict(decision)}


def not_applicable_by_rule(key: str) -> dict[str, Any]:
    """Permanence only matters where stored carbon can be reversed (e.g. forests, soils).

    For emission-avoidance activities (grid renewables, landfill gas, cookstoves) we
    decide this from the project category instead of asking the LLM, whose answer
    varied between 'not applicable' and 'no evidence' across runs.
    """
    return {
        "principle": key, "status": "not_applicable", "score": None,
        "rationale": "Emission-avoidance activity without stored carbon at risk of reversal; "
                     "permanence is not applicable (rule based on project category, not AI).",
        "quotes": [], "dropped_findings": 0, "llm": None, "decision": None, "rule": "no_reversal_risk",
    }


def overall_score(principles: list[dict[str, Any]]) -> dict[str, Any]:
    """Weighted mean over principles that have a numeric score; weights renormalized."""
    scored = [(BY_KEY[p["principle"]].weight, p["score"]) for p in principles if p["score"] is not None]
    if not scored:
        return {"score": None, "included": [], "excluded": [p["principle"] for p in principles]}
    total_w = sum(w for w, _ in scored)
    return {
        "score": round(sum(w * s for w, s in scored) / total_w),
        "included": [p["principle"] for p in principles if p["score"] is not None],
        "excluded": [p["principle"] for p in principles if p["score"] is None],
        "weights": {p.key: p.weight for p in PRINCIPLES},
    }


def _cached_assess(doc: Document, key: str, llm_client: ChatClient, verifier: QuoteVerifier,
                   cache_dir: Path | None) -> tuple[PrincipleResult, bool]:
    """LLM evidence extraction, cached per (document, principle, prompt version, model).

    LLM output varies between runs even with a fixed model; caching keeps the
    evidence stable so a re-run judges the same quotes. Failed runs are not cached.
    """
    path = None
    if cache_dir is not None:
        model = llm_client.settings.model.replace("/", "_")
        path = cache_dir / f"{doc.sha256[:16]}-{key}-{PROMPT_VERSION}-{model}.json"
        if path.exists():
            return PrincipleResult.from_dict(json.loads(path.read_text(encoding="utf-8"))), True
    llm = assess_principle(doc, BY_KEY[key], llm_client, verifier)
    if path is not None and llm.status != "assessment_failed":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(llm.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return llm, False


def build_report(
    doc: Document,
    project: dict[str, Any],
    llm_client: ChatClient,
    decision_model: DecisionModel,
    principle_keys: list[str] | None = None,
    cache_dir: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (report, run_log). The run log keeps costs and raw attempts out of the hashed report."""
    verifier = QuoteVerifier(doc)
    principles, run_log = [], {"llm": [], "decision_models": set()}
    for key in principle_keys or [p.key for p in PRINCIPLES]:
        if key == "permanence" and project.get("reversal_risk") is False:
            principles.append(not_applicable_by_rule(key))
            continue
        llm, cached = _cached_assess(doc, key, llm_client, verifier, cache_dir)
        run_log["llm"].append({"principle": key, "cached": cached, "served_model": llm.served_model,
                               "usage": None if cached else llm.usage, "error": llm.error,
                               "dropped": [vars(d) for d in llm.dropped]})
        entry = judge_principle(llm, decision_model)
        if entry["decision"]:
            run_log["decision_models"].add(entry["decision"]["model"])
        principles.append(entry)

    method = {
        "report_schema": REPORT_SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "question_set_version": QUESTION_SET_VERSION,
        "llm_model": llm_client.settings.model,
        "decision_model": decision_model.name,
        "decision_input": DECISION_INPUT,
        "methodology_table_version": load_table()["table_version"],
        "pdf_extractor": f"pymupdf {pymupdf.__version__}",
    }
    report = {
        "schema": REPORT_SCHEMA_VERSION,
        "project": {k: project.get(k) for k in ("project_id", "project_name", "registry_url",
                                                 "methodology", "methodology_version")},
        "document": {"file_name": project.get("file_name"), "sha256": doc.sha256, "pages": doc.page_count},
        "methodology_status": methodology_status(project["methodology"], project.get("methodology_version")),
        "method": method,
        "method_hash": hash_json(method),
        "principles": principles,
        "overall": overall_score(principles),
        "disclaimer": DISCLAIMER,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    run_log["decision_models"] = sorted(run_log["decision_models"])
    return report, run_log


def report_hash(report: dict[str, Any]) -> str:
    return hash_json(report)
