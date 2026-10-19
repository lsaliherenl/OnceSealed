"""Build the citation check: is the paragraph the model cited really evidence for the question?

    python scripts/build_citation_check.py

On 30,000-character excerpts (scripts/experiment_long_excerpt.py) the checklist answered "yes" on questions that
were "no" in the gold set's 2,500-character excerpts, each citing a paragraph from the extra text. Whether those
answers are right decides how large the report excerpts should be, so a person judges each cited paragraph.

To keep the judgement blind to the model, every unit is one paragraph and one question, and the model's citations
(up to two per question) are mixed with decoys: for other questions, the paragraph of the same excerpt that scores
highest on the principle's keywords without being cited. The annotator does not see which is which; the mapping is
in data/eval/citation_check/key.json (do not open it before labelling).

Writes data/eval/citation_check/{units.json, key.json, tool.html}. Exports go to data/eval/citation_check/labels/.
"""

import json
import random
import sys
from pathlib import Path

from core.ai.checklist import QUESTIONS
from core.ai.pdf_extract import extract_many
from core.ai.principles import BY_KEY
from core.ai.select import score_paragraph, select_paragraphs
from core.config import PROJECT_ROOT

EVAL = PROJECT_ROOT / "data" / "eval"
OUT = EVAL / "citation_check"
EXCERPT_CHARS = 30_000
CITES_PER_QUESTION = 2
DECOYS = 30
SEED = 20261019
# Documents read in the experiment: the project descriptions, plus the CDM PDD already attached to VCS1742.
# Monitoring and validation reports registered later are left out so paragraph ids match the experiment.
EXPERIMENT_EXTRAS = {"VCS1742"}

GUIDE_RULES = [
    "Yalnızca gösterilen paragrafa bak: kanıt bu paragrafta yoksa \"hayır\" (belgenin başka yerinde olabileceğini düşünme).",
    "Standardın gereklilik metni (ör. uyum tablosunun sol sütunu) kanıt sayılmaz; projenin kendi beyanı gerekir.",
    "Alan bilgisiyle çıkarım yapma; metin söylemeli.",
    "Belirli faaliyetler gelecek zamanla anlatılıyorsa sayılır; yalnızca genel niyet sayılmaz.",
    "Bir büyüklüğü ölçme yöntemi anlatılıyorsa konu ele alınmış sayılır.",
    "Adı verilen kurumlar katılımcı sayılır; plan veya rapor tarihleri görüşmenin ayrıntısı değildir.",
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    gold = json.loads((EVAL / "gold.json").read_text(encoding="utf-8"))
    exp = json.loads((EVAL / "experiments" / "long_excerpt_30k.json").read_text(encoding="utf-8"))
    items = {i["item_id"]: i for i in json.loads((EVAL / "items.json").read_text(encoding="utf-8"))["items"]}
    manifest = {d["project_id"]: d for d in
                json.loads((PROJECT_ROOT / "samples" / "manifest.json").read_text(encoding="utf-8"))["documents"]}

    excerpts: dict[str, dict] = {}
    for iid, item in items.items():
        proj = manifest[item["project_id"]]
        extras = proj.get("extra_files", []) if item["project_id"] in EXPERIMENT_EXTRAS else []
        doc = excerpts.setdefault(item["project_id"] + "#doc", extract_many(
            PROJECT_ROOT / proj["local_path"], [PROJECT_ROOT / f["local_path"] for f in extras]))
        paras = select_paragraphs(doc, BY_KEY[item["principle"]], budget_chars=EXCERPT_CHARS, overview_chars=0)
        excerpts[iid] = {p.id: p for p in paras}

    rng = random.Random(SEED)
    units, key = [], {}

    def add(iid: str, qid: str, pid: str, source: str) -> None:
        p = excerpts[iid][pid]
        uid = f"u{len(units) + 1:03d}"
        units.append({"uid": uid, "project_id": items[iid]["project_id"], "project_name": items[iid]["project_name"],
                      "question_id": qid, "paragraph_id": pid, "page": p.page, "text": p.text})
        key[uid] = {"source": source, "item_id": iid, "question_id": qid}

    targets = sorted(k for k in gold if gold[k] == "no" and exp[k]["answer"] == "yes")
    for k in targets:
        iid, qid = k.split("|")
        for pid in exp[k]["evidence"][:CITES_PER_QUESTION]:
            add(iid, qid, pid, "model_citation")

    # decoys: for questions outside the targets, an on-topic paragraph (keyword hit) the model did not cite, with a
    # length drawn from the citations' lengths so that length does not give the source away
    cited_lengths = [len(u["text"]) for u in units]
    pool = sorted(k for k in gold if k not in targets)
    rng.shuffle(pool)
    decoys = 0
    for k in pool:
        if decoys == DECOYS:
            break
        iid, qid = k.split("|")
        cited = set(exp[k]["evidence"] or [])
        kw = BY_KEY[items[iid]["principle"]].keywords
        target = rng.choice(cited_lengths)
        candidates = [p for pid, p in excerpts[iid].items() if pid not in cited and score_paragraph(p.text, kw) > 0]
        if candidates:
            best = min(candidates, key=lambda p: (abs(len(p.text) - target), -score_paragraph(p.text, kw)))
            add(iid, qid, best.id, "decoy")
            decoys += 1

    order = list(range(len(units)))
    rng.shuffle(order)
    shuffled = [units[i] for i in order]
    for n, u in enumerate(shuffled, 1):  # renumber in display order so ids carry no information
        old = u["uid"]
        u["uid"] = f"c{n:03d}"
        key[u["uid"]] = key.pop(old)
    key = dict(sorted(key.items()))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "labels").mkdir(exist_ok=True)
    questions = {q.id: {"text": q.text, "tr": q.tr, "yes_if": q.yes_if, "no_if": q.no_if} for q in QUESTIONS}
    data = {"version": "citation-check-v1", "excerpt_chars": EXCERPT_CHARS, "units": shuffled,
            "questions": questions, "rules": GUIDE_RULES}
    (OUT / "units.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "key.json").write_text(json.dumps({"seed": SEED, "targets": len(targets), "units": key}, indent=1) + "\n",
                                  encoding="utf-8")
    template = (Path(__file__).parent / "citation_check_template.html").read_text(encoding="utf-8")
    html = template.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (OUT / "tool.html").write_text(html, encoding="utf-8")
    n_model = sum(1 for v in key.values() if v["source"] == "model_citation")
    print(f"{len(targets)} questions, {n_model} cited paragraphs + {decoys} decoys = {len(shuffled)} units "
          f"-> {(OUT / 'tool.html').relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
