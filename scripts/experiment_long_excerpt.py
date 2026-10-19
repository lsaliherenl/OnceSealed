"""Experiment: the report checklist pipeline on 30,000-character excerpts (the report-v1 budget).

    python scripts/experiment_long_excerpt.py   ->  data/eval/experiments/long_excerpt_30k.json

Recall is measurable on the gold "yes" items (their evidence sits in the 2,500 excerpt, which the long excerpt
contains); new "yes" answers on gold "no" items are unverified (evidence may really be in the extra text).
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from core.ai.checklist_models import LLMChecklist
from core.ai.pdf_extract import extract_many
from core.ai.principles import BY_KEY
from core.ai.select import select_paragraphs
from core.config import PROJECT_ROOT

sys.stdout.reconfigure(encoding="utf-8")
gold = json.loads((PROJECT_ROOT / "data/eval/gold.json").read_text())
items = json.loads((PROJECT_ROOT / "data/eval/items.json").read_text(encoding="utf-8"))["items"]
manifest = {d["project_id"]: d for d in json.loads((PROJECT_ROOT / "samples/manifest.json").read_text(encoding="utf-8"))["documents"]}
docs = {}
for pid, proj in manifest.items():
    docs[pid] = extract_many(PROJECT_ROOT / proj["local_path"], [PROJECT_ROOT / f["local_path"] for f in proj.get("extra_files", [])])
llm = LLMChecklist()


def run(item):
    doc = docs[item["project_id"]]
    paras = select_paragraphs(doc, BY_KEY[item["principle"]], budget_chars=30_000, overview_chars=0)
    short = {p["id"] for p in item["paragraphs"]}
    contains = short <= {p.id for p in paras}
    r = llm.answer(item["principle"], paras)
    return item["item_id"], contains, sum(len(p.text) for p in paras), {q: (a.answer, a.evidence) for q, a in r.answers.items()}


with ThreadPoolExecutor(max_workers=6) as pool:
    results = list(pool.map(run, items))
out = {}
for iid, contains, chars, ans in results:
    for q, (a, ev) in ans.items():
        out[f"{iid}|{q}"] = {"answer": a, "evidence": ev, "contains_short": contains, "chars": chars}
(PROJECT_ROOT / "data/eval/experiments/long_excerpt_30k.json").write_text(json.dumps(out, indent=1))
yes = [k for k in gold if gold[k] == "yes"]
no = [k for k in gold if gold[k] == "no"]
print("items whose long excerpt contains the short one:", sum(c for _, c, _, _ in results), "/", len(results))
print("recall on gold yes:", sum(out[k]["answer"] == "yes" for k in yes), "/", len(yes))
print("gold no -> yes on long excerpt (unverified, maybe real evidence):", sum(out[k]["answer"] == "yes" for k in no), "/", len(no))
print("median excerpt chars:", sorted(c for _, _, c, _ in results)[len(results) // 2])
