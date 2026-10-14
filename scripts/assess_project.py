"""Produce the published quality report for a demo project listed in samples/manifest.json.

Usage:
    python scripts/assess_project.py VCS1851
    python scripts/assess_project.py VCS1851 --principles additionality safeguards

Writes:
    reports/<project_id>.json             published report (its keccak256 goes on-chain)
    data/runs/reports/<project_id>-<ts>.json   run log (costs, served models, dropped quotes)
    data/evidence/<project_id>.jsonl      evidence + question set, for training/evaluating other decision models
"""

import argparse
import json
import logging
import sys
import time

from core.ai.client import ChatClient
from core.ai.decision import JevDecisionModel, build_questions, QUESTION_SET_VERSION
from core.ai.pdf_extract import extract_many, file_sha256
from core.ai.principles import BY_KEY, PRINCIPLES
from core.ai.report import build_report, report_hash
from core.config import PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--principles", nargs="*", choices=list(BY_KEY))
    parser.add_argument("--no-cache", action="store_true", help="re-run the LLM even if cached evidence exists")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    manifest = json.loads((PROJECT_ROOT / "samples" / "manifest.json").read_text(encoding="utf-8"))
    project = next((d for d in manifest["documents"] if d["project_id"] == args.project_id), None)
    if project is None:
        sys.exit(f"{args.project_id} not in samples/manifest.json")

    files = [project] + project.get("extra_files", [])
    for f in files:
        if f.get("sha256") and f["sha256"] != file_sha256(PROJECT_ROOT / f["local_path"]):
            sys.exit(f"{f['local_path']} does not match the sha256 recorded in the manifest")
    doc = extract_many(PROJECT_ROOT / project["local_path"], [PROJECT_ROOT / f["local_path"] for f in files[1:]])

    cache = None if args.no_cache else PROJECT_ROOT / "data" / "cache" / "llm"
    report, run_log = build_report(doc, project, ChatClient(), JevDecisionModel(), args.principles, cache)
    rhash = report_hash(report)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = PROJECT_ROOT / "reports" / f"{args.project_id}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log_dir = PROJECT_ROOT / "data" / "runs" / "reports"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{args.project_id}-{stamp}.json").write_text(
        json.dumps({"report_hash": rhash, **run_log}, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    ev_dir = PROJECT_ROOT / "data" / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    with open(ev_dir / f"{args.project_id}.jsonl", "w", encoding="utf-8") as f:
        for p in report["principles"]:
            if not p["quotes"]:
                continue
            f.write(json.dumps({
                "project_id": args.project_id, "document_sha256": doc.sha256, "principle": p["principle"],
                "question_set_version": QUESTION_SET_VERSION, "questions": build_questions(BY_KEY[p["principle"]]),
                "state": [q["text"] for q in p["quotes"]], "quotes": p["quotes"],
            }, ensure_ascii=False) + "\n")

    ms = report["methodology_status"]
    print(f"{args.project_id}  {project['project_name']}")
    print(f"methodology {ms['code']} v{ms['version']}: {ms['status']}")
    for p in report["principles"]:
        d = p["decision"] or {}
        conf = f" conf={d['evidence_confidence']:.2f}" if d else ""
        flags = f" FLAGS={p['review_flags']}" if p.get("review_flags") else ""
        level = f" level={d['evidence_level']}" if d else ""
        said = f"LLM said {p['llm']['status']}/{p['llm']['score']}" if p["llm"] else f"rule: {p.get('rule')}"
        print(f"  {p['principle']:22s} {p['status']:18s} score={str(p['score']):>4s}{conf}{level}  "
              f"quotes={len(p['quotes'])} dropped={p['dropped_findings']}  ({said}){flags}")
    o = report["overall"]
    print(f"overall={o['score']}  included={o['included']}")
    llm_cost = sum((x["usage"] or {}).get("cost", 0) for x in run_log["llm"])
    print(f"llm cost=${llm_cost:.4f}  decision models={run_log['decision_models']}")
    print(f"method_hash={report['method_hash']}\nreport_hash={rhash}\n-> {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
