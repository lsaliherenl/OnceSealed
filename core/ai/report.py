"""Build the quality report for one project document.

Layer 1  methodology status  deterministic table lookup (core.ai.methodology)
Layer 2  evidence checklist  per principle, a code-selected excerpt and the checklist questions of
                             core.ai.checklist; the LLM answers yes/no and cites the paragraph holding the
                             evidence, a second model (Jev) answers the same questions, and a check where the two
                             disagree is flagged for human review. This is the setup measured against the labelled
                             gold set (docs/ai_evaluation.md), through the same code (core.ai.checklist_models).
Layer 3  principle status    deterministic: how many of the principle's checks found evidence

Paragraphs that read as instructions to an AI model are screened out of every excerpt first (core.ai.injection).

The report is published as JSON; its keccak256 over canonical JSON goes on-chain
together with ``method_hash``, which pins the models, questions, prompt and excerpt rule used.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pymupdf

from core.ai.checklist import BY_PRINCIPLE, QUESTION_SET_VERSION
from core.ai.checklist_models import (CHECKLIST_PROMPT_VERSION, EVIDENCE_RULE, Answer, ChecklistResult,
                                      JevChecklist, LLMChecklist)
from core.ai.methodology import load_table, methodology_status
from core.ai.injection import SCREEN_VERSION, screen
from core.ai.review import DECISIONS, REVIEW_RULE, final_answer
from core.ai.pdf_extract import Document, Paragraph
from core.ai.principles import BY_KEY, PRINCIPLES
from core.ai.select import select_paragraphs
from core.hashing import hash_json

log = logging.getLogger(__name__)

REPORT_SCHEMA_VERSION = "report-v2"
# The gold set was labelled on 2,500-character excerpts (scripts/build_label_set.py), but at that size the checks
# missed evidence in at least 46 of the 119 "not found" answers (data/eval/citation_check). On 30,000 characters the
# same checks still find 56 of the 58 known positives, and 46 of their 61 new findings were confirmed.
EXCERPT_CHARS = 30_000
EXCERPT_RULE = f"select_paragraphs(budget_chars={EXCERPT_CHARS}, overview_chars=0)"

DISCLAIMER = (
    "Signal, not verdict. Each check says whether a specific kind of evidence is present in an excerpt of the "
    "submitted documents, not whether the evidence is true. Scores are not an ICVCM assessment, a rating of the "
    "project, or a statement about its real-world impact."
)


def excerpt(doc: Document, principle: str) -> list[Paragraph]:
    return select_paragraphs(doc, BY_KEY[principle], budget_chars=EXCERPT_CHARS, overview_chars=0)


def principle_status(answers: list[str | None]) -> tuple[str, int | None]:
    """Status and 0-100 score from the checks' answers: the share of checks with evidence."""
    if not answers or any(a not in ("yes", "no") for a in answers):
        return "assessment_failed", None
    k = sum(a == "yes" for a in answers)
    status = "no_evidence" if k == 0 else "strong_evidence" if k == len(answers) else "partial_evidence"
    return status, round(100 * k / len(answers))


def judge_principle(principle: str, paragraphs: list[Paragraph], llm: ChecklistResult,
                    second: dict[str, float] | None,
                    reviews: dict[tuple[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Combine the LLM's checklist answers, the second model's probabilities and any person's decisions on
    flagged checks (core.ai.review) into one report entry."""
    by_id = {p.id: p for p in paragraphs}
    checks, flags, quotes = [], [], {}
    for q in BY_PRINCIPLE[principle]:
        a: Answer = llm.answers[q.id]
        p_yes = None if second is None else round(second[q.id], 4)
        disagree = p_yes is not None and a.answer in ("yes", "no") and (p_yes >= 0.5) != (a.answer == "yes")
        review = (reviews or {}).get((principle, q.id))
        if review and DECISIONS[review["decision"]] is not None:
            disagree = False  # a person decided; the models' answers stay in the entry
        if disagree:
            flags.append(f"models_disagree:{q.id}")
        evidence = [{"paragraph_id": i, "page": by_id[i].page, "text": by_id[i].text}
                    for i in a.evidence if i in by_id] if a.answer == "yes" else []
        for e in evidence:
            quotes.setdefault(e["paragraph_id"], e)
        check = {"id": q.id, "question": q.text, "answer": a.answer, "evidence": evidence,
                 "second_opinion_p_yes": p_yes, "needs_review": disagree, "dropped": a.dropped}
        if review:
            check["human_review"] = {k: review[k] for k in ("decision", "note", "reviewer", "reviewed_at")}
        checks.append(check)
    answers = [final_answer(c) for c in checks]
    status, score = principle_status(answers)
    found = [c["id"] for c, x in zip(checks, answers) if x == "yes"]
    missing = [c["id"] for c, x in zip(checks, answers) if x == "no"]
    decided = sum(1 for c in checks if c.get("human_review") and DECISIONS[c["human_review"]["decision"]] is not None)
    rationale = (f"Evidence found for {len(found)} of {len(checks)} checks"
                 + (f" ({', '.join(found)})" if found else "")
                 + (f"; not found in the excerpt: {', '.join(missing)}" if missing else "")
                 + (f"; {decided} decided by a person after the models disagreed" if decided else "") + ".")
    return {
        "principle": principle, "status": status, "score": score, "rationale": rationale,
        "checks": checks,
        "quotes": [{"text": e["text"], "page": e["page"], "paragraph_id": e["paragraph_id"],
                    "verification": "cited_paragraph"} for e in quotes.values()],
        "dropped_findings": sum(1 for c in checks if c["dropped"]),
        "review_flags": flags,
        "excerpt": {"paragraphs": [p.id for p in paragraphs], "chars": sum(len(p.text) for p in paragraphs)},
    }


def not_applicable_by_rule(key: str) -> dict[str, Any]:
    """Permanence only matters where stored carbon can be reversed (e.g. forests, soils).

    For emission-avoidance activities (grid renewables, landfill gas, cookstoves) we
    decide this from the project category instead of asking a model.
    """
    return {
        "principle": key, "status": "not_applicable", "score": None,
        "rationale": "Emission-avoidance activity without stored carbon at risk of reversal; "
                     "permanence is not applicable (rule based on project category, not AI).",
        "checks": [], "quotes": [], "dropped_findings": 0, "review_flags": [], "rule": "no_reversal_risk",
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


def _cached_checklist(doc: Document, principle: str, paragraphs: list[Paragraph], llm: LLMChecklist,
                      cache_dir: Path | None) -> tuple[ChecklistResult, bool]:
    """LLM checklist answers, cached per (excerpt, principle, prompt, evidence rule, model).

    The LLM's answers vary a little between runs; caching keeps a re-run on the same excerpt stable. The key
    hashes the excerpt itself, so a change of excerpt size or of the documents read asks the model again.
    Results with a missing answer are not cached.
    """
    path = None
    if cache_dir is not None:
        model = llm.name.replace("/", "_")
        ex = hash_json({"document": doc.sha256, "paragraphs": [[p.id, p.text] for p in paragraphs]})[2:18]
        path = cache_dir / f"{ex}-{principle}-{CHECKLIST_PROMPT_VERSION}-{EVIDENCE_RULE}-{model}.json"
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
            answers = {k: Answer(**v) for k, v in d.pop("answers").items()}
            return ChecklistResult(answers=answers, **d), True
    result = llm.answer(principle, paragraphs)
    if path is not None and all(a.answer in ("yes", "no") for a in result.answers.values()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False), encoding="utf-8")
    return result, False


def build_report(
    doc: Document,
    project: dict[str, Any],
    llm: LLMChecklist,
    second: JevChecklist | None,
    principle_keys: list[str] | None = None,
    cache_dir: Path | None = None,
    on_principle: Callable[[str], None] | None = None,
    reviews: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (report, run_log). The run log keeps costs and served models out of the hashed report.
    ``on_principle`` is called with each principle's key when it is done (progress for the API)."""
    principles, run_log = [], {"llm": [], "second_opinion": []}
    for key in principle_keys or [p.key for p in PRINCIPLES]:
        if key == "permanence" and project.get("reversal_risk") is False:
            principles.append(not_applicable_by_rule(key))
            if on_principle:
                on_principle(key)
            continue
        # instruction-like paragraphs (prompt injection) never reach a model; they are listed for a person
        paragraphs, screened_out = screen(excerpt(doc, key))
        result, cached = _cached_checklist(doc, key, paragraphs, llm, cache_dir)
        run_log["llm"].append({"principle": key, "cached": cached, "served_model": result.served_model,
                               "cost": None if cached else result.cost, "calls": result.calls})
        probs = None
        if second is not None:
            try:
                probs, data = second.probabilities(key, paragraphs)
                run_log["second_opinion"].append({"principle": key, "model": data.get("model"),
                                                  "cost": (data.get("usage") or {}).get("cost")})
            except Exception as e:  # the second opinion is optional; its absence is flagged in the report
                log.warning("second opinion failed for %s: %s", key, e)
                run_log["second_opinion"].append({"principle": key, "error": str(e)})
        entry = judge_principle(key, paragraphs, result, probs, reviews)
        if screened_out:
            entry["screened_out"] = screened_out
            entry["review_flags"].append("instruction_like_text")
        if second is not None and probs is None:
            entry["review_flags"].append("second_opinion_failed")
        principles.append(entry)
        if on_principle:
            on_principle(key)

    method = {
        "report_schema": REPORT_SCHEMA_VERSION,
        "question_set_version": QUESTION_SET_VERSION,
        "prompt_version": CHECKLIST_PROMPT_VERSION,
        "evidence_rule": EVIDENCE_RULE,
        "excerpt_rule": EXCERPT_RULE,
        "injection_screen": SCREEN_VERSION,
        "review_rule": REVIEW_RULE,
        "llm_model": llm.name,
        "second_opinion_model": second.name if second else None,
        "methodology_table_version": load_table()["table_version"],
        "pdf_extractor": f"pymupdf {pymupdf.__version__}",
    }
    report = {
        "schema": REPORT_SCHEMA_VERSION,
        "project": {k: project.get(k) for k in ("project_id", "project_name", "registry_url",
                                                 "methodology", "methodology_version")},
        "document": {"file_name": project.get("file_name"), "sha256": doc.sha256, "pages": doc.page_count,
                     **({"extra_files": [{"file_name": f["file_name"], "sha256": f["sha256"]}
                                         for f in project["extra_files"]]} if project.get("extra_files") else {})},
        "methodology_status": methodology_status(project["methodology"], project.get("methodology_version")),
        "method": method,
        "method_hash": hash_json(method),
        "principles": principles,
        "overall": overall_score(principles),
        "disclaimer": DISCLAIMER,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    return report, run_log


def report_hash(report: dict[str, Any]) -> str:
    return hash_json(report)
