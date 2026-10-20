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

from core.ai import assessment
from core.ai.checklist_models import JevChecklist, LLMChecklist
from core.ai.principles import BY_KEY
from core.config import PROJECT_ROOT


def assess(project: dict, llm: LLMChecklist, second: JevChecklist | None, principles: list[str] | None,
           use_cache: bool) -> None:
    pid = project["project_id"]
    try:
        a = assessment.run(project, llm, second, principles, use_cache)
    except ValueError as e:
        sys.exit(str(e))
    assessment.save(pid, a)

    report = a.report
    ms = report["methodology_status"]
    print(f"{pid}  {project['project_name']}")
    print(f"  methodology {ms['code']} v{ms['version']}: {ms['status']}")
    for p in report["principles"]:
        answers = " ".join(f"{c['id']}={'Y' if c['answer'] == 'yes' else 'n'}" for c in p["checks"])
        flags = f"  review={p['review_flags']}" if p["review_flags"] else ""
        print(f"  {p['principle']:22s} {p['status']:17s} score={str(p['score']):>4s}  {answers}"
              f"  dropped={p['dropped_findings']}{flags}")
    print(f"  overall={report['overall']['score']}  cost=${a.cost:.4f}  report_hash={a.report_hash}")


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
