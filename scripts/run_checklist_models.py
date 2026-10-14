"""D1: ask the decision model (Jev 1.13) and the LLM the checklist questions on every evaluation item.

    python scripts/run_checklist_models.py --runs 3

Both models see exactly the excerpt the human annotators see (data/eval/items.json).
Writes data/eval/answers_jev.json and data/eval/answers_llm.json:
    {"model": ..., "runs": [ {item_id|question_id: {...}}, ... ]}
Jev gives a probability of "yes"; the LLM gives yes/no plus an evidence paragraph id.
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import json_repair

from core.ai.checklist import BY_PRINCIPLE, QUESTION_SET_VERSION
from core.ai.client import ChatClient
from core.ai.decision import JevDecisionModel
from core.config import PROJECT_ROOT

EVAL = PROJECT_ROOT / "data" / "eval"

LLM_SYSTEM = """You check whether specific kinds of evidence are present in an excerpt of a carbon project document.
Answer each question about the excerpt ONLY: "yes" if the excerpt itself contains that evidence, otherwise "no".
Do not use outside knowledge and do not guess what the rest of the document says.
For every "yes", give the id of the paragraph (shown in square brackets) that contains the evidence.
Respond with JSON only."""

RETRY_NOTE = "\n\nReturn ONLY the JSON object with one answer per question id."

LLM_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["answers"],
    "properties": {"answers": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "answer", "evidence"],
        "properties": {"id": {"type": "string"}, "answer": {"type": "string", "enum": ["yes", "no"]},
                       "evidence": {"type": ["string", "null"]}}}}},
}


def excerpt_lines(item: dict[str, Any]) -> list[str]:
    return [f"[{p['id']}] {' '.join(p['text'].split())}" for p in item["paragraphs"]] or ["(no relevant paragraphs)"]


def ask_jev(jev: JevDecisionModel, item: dict[str, Any]) -> dict[str, Any]:
    qs = BY_PRINCIPLE[item["principle"]]
    body = {"model": jev.name, "state": excerpt_lines(item), "questions": {
        q.id: {"type": "noul", "instructions": q.text + " Judge only the text provided; answer about this excerpt."}
        for q in qs}}
    t0 = time.perf_counter()
    data = jev._post(body)
    ms = (time.perf_counter() - t0) * 1000
    return {f"{item['item_id']}|{q.id}": {"p_yes": data["answers"][q.id]["noul"], "model": data.get("model"),
                                           "latency_ms": round(ms), "cost": (data.get("usage") or {}).get("cost")}
            for q in qs}


def ask_llm(client: ChatClient, item: dict[str, Any]) -> dict[str, Any]:
    qs = BY_PRINCIPLE[item["principle"]]
    user = ("Excerpt:\n" + "\n\n".join(excerpt_lines(item)) + "\n\nQuestions:\n"
            + "\n".join(f"{q.id}: {q.text}" for q in qs))
    t0 = time.perf_counter()
    answers, cost, out = {}, 0.0, None
    for attempt in range(3):  # retry when the output cannot be parsed or answers are missing
        prompt = user if attempt == 0 else user + RETRY_NOTE
        out = client.complete_json(LLM_SYSTEM, prompt, "checklist_answers", LLM_SCHEMA, max_tokens=3000)
        cost += (out.usage or {}).get("cost") or 0
        answers = _parse_answers(out.content)
        if all(q.id in answers and answers[q.id].get("answer") in ("yes", "no") for q in qs):
            break
    ms = (time.perf_counter() - t0) * 1000
    return {f"{item['item_id']}|{q.id}": {"answer": answers.get(q.id, {}).get("answer"),
                                           "evidence": answers.get(q.id, {}).get("evidence"),
                                           "model": out.served_model, "latency_ms": round(ms), "cost": cost}
            for q in qs}


def _parse_answers(content: str) -> dict[str, dict[str, Any]]:
    text = content.strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = json_repair.loads(text)
    try:
        return {a["id"]: a for a in data["answers"]}
    except (KeyError, TypeError):
        return {}


def run(name: str, fn, items: list[dict[str, Any]], runs: int) -> None:
    all_runs = []
    for r in range(runs):
        with ThreadPoolExecutor(max_workers=6) as pool:
            parts = list(pool.map(fn, items))
        merged = {k: v for part in parts for k, v in part.items()}
        all_runs.append(merged)
        missing = sum(1 for v in merged.values() if v.get("answer", v.get("p_yes")) is None)
        print(f"  {name} run {r + 1}/{runs}: {len(merged)} answers, {missing} missing")
    out = {"question_set_version": QUESTION_SET_VERSION, "model": name, "runs": all_runs}
    (EVAL / f"answers_{name}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--models", nargs="*", default=["jev", "llm"])
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    items = json.loads((EVAL / "items.json").read_text(encoding="utf-8"))["items"]
    if "jev" in args.models:
        jev = JevDecisionModel()
        run("jev", lambda it: ask_jev(jev, it), items, args.runs)
    if "llm" in args.models:
        client = ChatClient()
        run("llm", lambda it: ask_llm(client, it), items, args.runs)


if __name__ == "__main__":
    main()
