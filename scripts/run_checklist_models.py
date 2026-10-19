"""D1: answer the checklist questions on every evaluation item with the models.

    python scripts/run_checklist_models.py --models report --runs 3
    python scripts/run_checklist_models.py --models jev llm --runs 3

Every model sees exactly the excerpt the annotators saw (data/eval/items.json). Writes data/eval/answers_<name>.json:
    {"model": ..., "runs": [ {item_id|question_id: {...}}, ... ]}

    jev     Jev 1.13 probability of "yes" (the reports' second opinion)
    llm     the LLM's raw yes/no, as first measured (before the evidence rule)
    report  the published reports' answers: the same LLM and prompt, with the evidence rule of
            core.ai.checklist_models (a "yes" must cite a paragraph of the excerpt)
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from core.ai.checklist import BY_PRINCIPLE, QUESTION_SET_VERSION
from core.ai.checklist_models import CHECKLIST_PROMPT_VERSION, EVIDENCE_RULE, JevChecklist, LLMChecklist
from core.ai.pdf_extract import Paragraph
from core.config import PROJECT_ROOT

EVAL = PROJECT_ROOT / "data" / "eval"


def paragraphs(item: dict[str, Any]) -> list[Paragraph]:
    return [Paragraph(p["id"], p["page"], p["text"]) for p in item["paragraphs"]]


def ask_jev(jev: JevChecklist, item: dict[str, Any]) -> dict[str, Any]:
    t0 = time.perf_counter()
    probs, data = jev.probabilities(item["principle"], paragraphs(item))
    ms = round((time.perf_counter() - t0) * 1000)
    return {f"{item['item_id']}|{q}": {"p_yes": p, "model": data.get("model"), "latency_ms": ms,
                                       "cost": (data.get("usage") or {}).get("cost")} for q, p in probs.items()}


def ask_llm(llm: LLMChecklist, item: dict[str, Any], evidence_rule: bool) -> dict[str, Any]:
    r = llm.answer(item["principle"], paragraphs(item))
    out = {}
    for q in BY_PRINCIPLE[item["principle"]]:
        a = r.answers[q.id]
        answer = a.answer if evidence_rule else a.model_said
        out[f"{item['item_id']}|{q.id}"] = {"answer": answer, "evidence": ", ".join(a.evidence) or None,
                                            "model_said": a.model_said, "dropped": a.dropped,
                                            "model": r.served_model, "latency_ms": r.latency_ms, "cost": r.cost}
    return out


def run(name: str, fn: Callable[[dict[str, Any]], dict[str, Any]], items: list[dict[str, Any]], runs: int,
        meta: dict[str, Any]) -> None:
    all_runs = []
    for r in range(runs):
        with ThreadPoolExecutor(max_workers=6) as pool:
            parts = list(pool.map(fn, items))
        merged = {k: v for part in parts for k, v in part.items()}
        all_runs.append(merged)
        missing = sum(1 for v in merged.values() if v.get("answer", v.get("p_yes")) is None)
        dropped = sum(1 for v in merged.values() if v.get("dropped"))
        print(f"  {name} run {r + 1}/{runs}: {len(merged)} answers, {missing} missing, {dropped} yes dropped")
    out = {"question_set_version": QUESTION_SET_VERSION, "model": name, **meta, "runs": all_runs}
    (EVAL / f"answers_{name}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--models", nargs="*", default=["report"], choices=["jev", "llm", "report"])
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    items = json.loads((EVAL / "items.json").read_text(encoding="utf-8"))["items"]
    if "jev" in args.models:
        jev = JevChecklist()
        run("jev", lambda it: ask_jev(jev, it), items, args.runs, {})
    if {"llm", "report"} & set(args.models):
        llm = LLMChecklist()
    if "llm" in args.models:
        run("llm", lambda it: ask_llm(llm, it, evidence_rule=False), items, args.runs, {})
    if "report" in args.models:
        run("report", lambda it: ask_llm(llm, it, evidence_rule=True), items, args.runs,
            {"label": "Report pipeline (LLM + evidence rule)", "llm_model": llm.name,
             "prompt_version": CHECKLIST_PROMPT_VERSION, "evidence_rule": EVIDENCE_RULE})


if __name__ == "__main__":
    main()
