"""D1 pilot: score the models against provisional AI-made labels (data/eval/silver/*.json).

    python scripts/pilot_metrics.py

Writes docs/ai_evaluation_pilot.md. This is a dry run of the evaluation, not an accuracy measurement: the
reference labels come from an AI model, so agreement with them says how close the models are to that model's
reading, nothing more. Human labels (scripts/eval_metrics.py) replace it.
"""

import json
import statistics as st
import sys
from collections import defaultdict

from core.ai.checklist import QUESTIONS
from core.config import PROJECT_ROOT
from scripts.eval_metrics import EVAL, LABELS, load_models, model_yes, pct, prf

Q_PRINCIPLE = {q.id: q.principle for q in QUESTIONS}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ref_file = next((EVAL / "silver").glob("*.json"))
    ref_doc = json.loads(ref_file.read_text(encoding="utf-8"))
    ref = {f"{x['item_id']}|{x['question_id']}": x["answer"] for x in ref_doc["labels"]}
    models = load_models()
    keys = sorted(k for k, v in ref.items() if v in ("yes", "no"))
    gold = [ref[k] == "yes" for k in keys]
    names = {n: LABELS.get(n, a.get("label", n)) for n, a in models.items()}

    md = ["# AI evaluation pilot (provisional AI-made reference labels)", "",
          "> **Not an accuracy result.** The reference labels below were made by an AI model "
          f"(`{ref_doc['annotator']}`), blind to the model answers, using the same excerpts and labelling guide as the "
          "human annotators. They are a dry run of the evaluation and a way to find broken questions early. "
          "An LLM-made reference may favour the LLM under test. Human labels replace this file.", "",
          f"Reference: {len(keys)} of {len(ref)} questions answered yes/no ({sum(gold)} yes, "
          f"{pct(sum(gold) / len(gold))}); {len(ref) - len(keys)} marked unclear and left out.", "",
          "## Overall (positive class = evidence present), run 1", "",
          "| Model | Agreement | Precision | Recall | F1 | Brier | Yes-rate |", "|---|---|---|---|---|---|---|"]
    per_principle = defaultdict(dict)
    per_question = defaultdict(dict)
    for n, a in models.items():
        run = a["runs"][0]
        pred = [model_yes(n, run, k) for k in keys]
        m = prf(pred, gold)
        probs = [run[k]["p_yes"] for k in keys] if all("p_yes" in run[k] for k in keys) else None
        brier = f"{st.mean((p - g) ** 2 for p, g in zip(probs, gold)):.3f}" if probs else "-"
        md.append(f"| {names[n]} | {pct(m['accuracy'])} | {m['precision']:.2f} | {m['recall']:.2f} | "
                  f"{m['f1']:.2f} | {brier} | {pct(sum(pred) / len(pred))} |")
        for group, table in (("principle", per_principle), ("question", per_question)):
            buckets = defaultdict(list)
            for i, k in enumerate(keys):
                qid = k.split("|")[1]
                buckets[Q_PRINCIPLE[qid] if group == "principle" else qid].append(i)
            for g, idx in buckets.items():
                table[g][n] = prf([pred[i] for i in idx], [gold[i] for i in idx])
    base = st.mean((sum(gold) / len(gold) - g) ** 2 for g in gold)
    md += ["", f"Brier: 0 is perfect; always answering the reference's base rate scores {base:.3f}. "
           "Only models that return probabilities have one.", "",
           "## By principle (F1, `n/a` = no evidence present and none predicted)", "",
           "| Principle | n | " + " | ".join(names.values()) + " |", "|---|---|" + "---|" * len(models)]
    for p, row in per_principle.items():
        cells = ["n/a" if row[n]["f1"] is None else f"{row[n]['f1']:.2f}" for n in models]
        md.append(f"| {p} | {next(iter(row.values()))['n']} | " + " | ".join(cells) + " |")
    md += ["", "## By question (F1)", "", "| Question | n | yes in reference | " + " | ".join(names.values()) + " |",
           "|---|---|---|" + "---|" * len(models)]
    for q in QUESTIONS:
        if q.id in per_question:
            row = per_question[q.id]
            first = next(iter(row.values()))
            cells = ["n/a" if row[n]["f1"] is None else f"{row[n]['f1']:.2f}" for n in models]
            md.append(f"| {q.id} | {first['n']} | {first['tp'] + first['fn']} | " + " | ".join(cells) + " |")
    out = PROJECT_ROOT / "docs" / "ai_evaluation_pilot.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
