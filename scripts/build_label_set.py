"""D1: build the evaluation item set (data/eval/items.json) - one excerpt per (project, principle).

    python scripts/build_label_set.py

Each excerpt is chosen by code (keyword relevance, no LLM involved) and capped at EXCERPT_CHARS so
two people can label all items in a few hours. Humans, Jev and the LLM all answer the checklist
questions on exactly the same excerpt. Permanence is skipped for projects without reversal risk.
Deterministic: re-running produces the same file.
"""

import json
import sys

from core.ai.checklist import BY_PRINCIPLE, QUESTION_SET_VERSION
from core.ai.pdf_extract import extract_many
from core.ai.principles import PRINCIPLES
from core.ai.select import select_paragraphs
from core.config import PROJECT_ROOT

EXCERPT_CHARS = 2_500


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    # The labelled set is frozen: excerpts change when documents are added to the manifest, and the gold labels
    # (data/eval/gold.json) only hold for the excerpts they were given on. A new set goes in a new file.
    if (PROJECT_ROOT / "data" / "eval" / "gold.json").exists() and "--force" not in sys.argv:
        sys.exit("data/eval/items.json is labelled (gold.json exists); it is frozen. Pass --force to rebuild anyway.")
    manifest = json.loads((PROJECT_ROOT / "samples" / "manifest.json").read_text(encoding="utf-8"))["documents"]
    items = []
    for proj in manifest:
        extra = [PROJECT_ROOT / f["local_path"] for f in proj.get("extra_files", [])]
        doc = extract_many(PROJECT_ROOT / proj["local_path"], extra)
        for principle in PRINCIPLES:
            if principle.key == "permanence" and proj.get("reversal_risk") is False:
                continue
            paras = select_paragraphs(doc, principle, budget_chars=EXCERPT_CHARS, overview_chars=0)
            items.append({
                "item_id": f"{proj['project_id']}-{principle.key}",
                "project_id": proj["project_id"],
                "project_name": proj["project_name"],
                "category": proj["category"],
                "principle": principle.key,
                "questions": [q.id for q in BY_PRINCIPLE[principle.key]],
                "paragraphs": [{"id": p.id, "page": p.page, "text": p.text} for p in paras],
                "excerpt_chars": sum(len(p.text) for p in paras),
            })
        print(f"{proj['project_id']:8s} {sum(1 for i in items if i['project_id'] == proj['project_id'])} items")
    out = {"question_set_version": QUESTION_SET_VERSION, "excerpt_chars_max": EXCERPT_CHARS,
           "items": items, "labels_total": sum(len(i["questions"]) for i in items)}
    path = PROJECT_ROOT / "data" / "eval" / "items.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(PROJECT_ROOT)}: {len(items)} items, {out['labels_total']} yes/no labels, "
          f"{sum(i['excerpt_chars'] for i in items):,} characters to read")


if __name__ == "__main__":
    main()
