"""D1: export the checklist as (instruction, query, document) rows for a yes/no reranker such as Turnike 4B.

    python scripts/export_reranker_inputs.py

Writes data/eval/reranker_inputs.jsonl, one row per item x question (177 rows):
    {"key": "<item_id>|<question_id>", "instruction": ..., "query": <question>, "document": <excerpt>}

The excerpt is exactly what the annotators, Jev 1.13 and the LLM see. The model owner returns
data/eval/answers_<model>.json in the same shape as answers_jev.json:
    {"model": "<name>", "runs": [{"<key>": {"p_yes": 0.83, "latency_ms": 120, "cost": 0}, ...}, ...]}
and scripts/eval_metrics.py picks it up automatically. Use these rows for evaluation only, never for training.
"""

import json

from core.ai.checklist import BY_PRINCIPLE, QUESTION_SET_VERSION
from core.config import PROJECT_ROOT

EVAL = PROJECT_ROOT / "data" / "eval"
INSTRUCTION = ("Given an excerpt of a carbon project document, judge whether the excerpt itself contains the "
               "evidence the question asks about. Judge only the text provided.")


def main() -> None:
    items = json.loads((EVAL / "items.json").read_text(encoding="utf-8"))["items"]
    rows = []
    for item in items:
        doc = "\n".join(f"[{p['id']}] {' '.join(p['text'].split())}" for p in item["paragraphs"]) \
            or "(no relevant paragraphs)"
        for q in BY_PRINCIPLE[item["principle"]]:
            rows.append({"key": f"{item['item_id']}|{q.id}", "question_set_version": QUESTION_SET_VERSION,
                         "instruction": INSTRUCTION, "query": q.text, "document": doc})
    out = EVAL / "reranker_inputs.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
