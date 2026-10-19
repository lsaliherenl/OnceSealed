"""Produce the published quality report for a project listed in samples/manifest.json.

Usage:
    python scripts/assess_project.py VCS1851
    python scripts/assess_project.py VCS1851 --principles additionality safeguards
    python scripts/assess_project.py --all

Writes:
    reports/<project_id>.json                   published report (its keccak256 goes on-chain)
    data/runs/reports/<project_id>-<ts>.json    run log (costs, served models)
    data/evidence/<project_id>.jsonl            excerpts + checklist questions, for evaluating other decision models
"""

import argparse
import json
import logging
import sys
import time

from core.ai.checklist import BY_PRINCIPLE, QUESTION_SET_VERSION
from core.ai.checklist_models import JevChecklist, LLMChecklist
from core.ai.pdf_extract import extract_many, file_sha256
from core.ai.principles import BY_KEY
from core.ai.report import build_report, report_hash
from core.config import PROJECT_ROOT


def assess(project: dict, llm: LLMChecklist, second: JevChecklist | None, principles: list[str] | None,
           use_cache: bool) -> None:
    pid = project["project_id"]
    files = [project] + project.get("extra_files", [])
    for f in files:
        if f.get("sha256") and f["sha256"] != file_sha256(PROJECT_ROOT / f["local_path"]):
            sys.exit(f"{f['local_path']} does not match the sha256 recorded in the manifest")
    doc = extract_many(PROJECT_ROOT / project["local_path"], [PROJECT_ROOT / f["local_path"] for f in files[1:]])

    cache = PROJECT_ROOT / "data" / "cache" / "checklist" if use_cache else None
    report, run_log = build_report(doc, project, llm, second, principles, cache)
    rhash = report_hash(report)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = PROJECT_ROOT / "reports" / f"{pid}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log_dir = PROJECT_ROOT / "data" / "runs" / "reports"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{pid}-{stamp}.json").write_text(
        json.dumps({"report_hash": rhash, **run_log}, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    ev_dir = PROJECT_ROOT / "data" / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    by_id = {p.id: p for p in doc.paragraphs}
    with open(ev_dir / f"{pid}.jsonl", "w", encoding="utf-8") as f:
        for p in report["principles"]:
            if not p["checks"]:
                continue
            f.write(json.dumps({
                "project_id": pid, "document_sha256": doc.sha256, "principle": p["principle"],
                "question_set_version": QUESTION_SET_VERSION,
                "questions": [{"id": q.id, "text": q.text} for q in BY_PRINCIPLE[p["principle"]]],
                "paragraphs": [{"id": i, "page": by_id[i].page, "text": by_id[i].text}
                               for i in p["excerpt"]["paragraphs"]],
            }, ensure_ascii=False) + "\n")

    ms = report["methodology_status"]
    print(f"{pid}  {project['project_name']}")
    print(f"  methodology {ms['code']} v{ms['version']}: {ms['status']}")
    for p in report["principles"]:
        answers = " ".join(f"{c['id']}={'Y' if c['answer'] == 'yes' else 'n'}" for c in p["checks"])
        flags = f"  review={p['review_flags']}" if p["review_flags"] else ""
        print(f"  {p['principle']:22s} {p['status']:17s} score={str(p['score']):>4s}  {answers}"
              f"  dropped={p['dropped_findings']}{flags}")
    cost = sum(x["cost"] or 0 for x in run_log["llm"]) + sum(x.get("cost") or 0 for x in run_log["second_opinion"])
    print(f"  overall={report['overall']['score']}  cost=${cost:.4f}  report_hash={rhash}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id", nargs="?")
    parser.add_argument("--all", action="store_true", help="every project in the manifest")
    parser.add_argument("--principles", nargs="*", choices=list(BY_KEY))
    parser.add_argument("--no-cache", action="store_true", help="re-ask the LLM even if cached answers exist")
    parser.add_argument("--no-second-opinion", action="store_true", help="skip the second model (Jev)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    manifest = json.loads((PROJECT_ROOT / "samples" / "manifest.json").read_text(encoding="utf-8"))["documents"]
    if args.all:
        projects = manifest
    else:
        projects = [d for d in manifest if d["project_id"] == args.project_id]
        if not projects:
            sys.exit(f"{args.project_id} not in samples/manifest.json (or pass --all)")
    llm = LLMChecklist()
    second = None if args.no_second_opinion else JevChecklist()
    for project in projects:
        assess(project, llm, second, args.principles, not args.no_cache)


if __name__ == "__main__":
    main()
