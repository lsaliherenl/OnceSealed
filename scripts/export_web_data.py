"""Export the public data the web UI renders into web/src/data/site.json.

The project pages are static: they show the published reports in reports/, the methodology table,
the simulated issuance batches and the Sepolia deployment, all read here at build time. The published report
files are copied unchanged to web/public/reports/, so the browser can hash the file itself (src/lib/hashing.ts)
and compare it with `latestReport` on-chain without trusting this file. Run after a report, data check, batch or
deployment changes:

    python scripts/export_web_data.py
"""

import json
import shutil
from typing import Any

from core.config import PROJECT_ROOT
from core.data.batches import load_batches
from core.hashing import hash_json
from core.reports import history_path

OUT = PROJECT_ROOT / "web" / "src" / "data" / "site.json"
PUBLIC_REPORTS = PROJECT_ROOT / "web" / "public" / "reports"
SEPOLIA = 11155111
EXPLORER = "https://sepolia.etherscan.io"

# Host countries, from each project's registry page (not in the manifest).
COUNTRY = {
    "VCS1477": "Indonesia", "VCS1851": "India", "VCS138": "United States", "VCS2505": "South Africa",
    "VCS1742": "India", "VCS1728": "India", "VCS2609": "Malaysia", "VCS673": "Uganda", "VCS2846": "China",
    "VCS985": "Peru", "VCS4150": "Rwanda",
}


def _read(path: str) -> Any:
    return json.loads((PROJECT_ROOT / path).read_text(encoding="utf-8"))


def _principle(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "principle": p["principle"], "status": p["status"], "score": p.get("score"),
        "rationale": p.get("rationale", ""), "dropped_findings": p.get("dropped_findings", 0),
        "review_flags": p.get("review_flags", []),
        "checks": [{k: c[k] for k in ("id", "question", "answer", "evidence", "second_opinion_p_yes", "needs_review",
                                      "dropped")} for c in p.get("checks", [])],
        "excerpt_chars": (p.get("excerpt") or {}).get("chars"),
        "screened_out": p.get("screened_out", []),
    }


def _documents(doc: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """The files a report read, in extraction order: paragraph ids of extra file k start with "x<k>-".
    Roles come from the manifest (samples/manifest.json)."""
    roles = {f["file_name"]: f.get("role", "supporting") for f in manifest.get("extra_files", [])}
    main = {"prefix": "", "file_name": doc["file_name"], "role": "project_description"}
    return [main] + [{"prefix": f"x{k}-", "file_name": f["file_name"], "role": roles.get(f["file_name"], "supporting")}
                     for k, f in enumerate(doc.get("extra_files", []), start=1)]


def _robustness() -> dict[str, Any] | None:
    """Label-free robustness tests of the checklist (scripts/robustness_tests.py)."""
    path = PROJECT_ROOT / "data" / "eval" / "robustness.json"
    if not path.exists():
        return None
    r = json.loads(path.read_text(encoding="utf-8"))
    by = {(e["test"], e["variant"]): e for e in r["summary"]}
    pick = lambda e: {k: e[k] for k in ("questions", "right_before", "changed_by_test", "as_expected")
                      if k in e} | ({"screen_catches_it": e["screen_catches_it"]} if "screen_catches_it" in e else {})
    return {"screen": r["screen"], "source": "docs/ai_robustness.md",
            "evidence_removed": pick(by[("evidence_removed", "-")]), "irrelevant": pick(by[("irrelevant", "-")]),
            "inject_yes": {v: pick(by[("inject_yes", v)]) for t, v in by if t == "inject_yes"},
            "inject_no": pick(by[("inject_no", "explicit")])}


def _evaluation() -> dict[str, Any] | None:
    """Accuracy of the report pipeline on the labelled gold set (scripts/eval_metrics.py)."""
    path = PROJECT_ROOT / "data" / "eval" / "metrics.json"
    if not path.exists():
        return None
    m = json.loads(path.read_text(encoding="utf-8"))
    model = m["models"].get("report")
    if model is None:
        return None
    cc_path = PROJECT_ROOT / "data" / "eval" / "citation_check" / "summary.json"
    cc = next(iter(json.loads(cc_path.read_text(encoding="utf-8")).values()), None) if cc_path.exists() else None
    return {"questions": m["gold"]["questions"], "kappa": m["gold"]["kappa"], "annotators": m["gold"]["annotators"],
            "accuracy": model["accuracy"], "accuracy_ci95": model["accuracy_ci95"], "label": model["label"],
            "per_question": model["per_question"], "source": "docs/ai_evaluation.md",
            "long_excerpt": cc and {"questions": cc["questions"], "confirmed": cc["confirmed"],
                                    "confirmed_ci95": cc["confirmed_ci95"], "judged_by": cc["kind"],
                                    "human_check": cc.get("human_check"), "source": "docs/citation_check.md"},
            "robustness": _robustness()}


def main() -> None:
    deployment = _read(f"deployments/{SEPOLIA}.json")
    seed = _read(f"deployments/{SEPOLIA}-seed.json")
    if seed["contract"].lower() != deployment["address"].lower():
        raise SystemExit("seed log is for another contract; re-run scripts/seed_sepolia.py first")
    table = _read("core/ai/methodology_status.json")

    projects = []
    shutil.rmtree(PUBLIC_REPORTS, ignore_errors=True)
    PUBLIC_REPORTS.mkdir(parents=True)

    # every anchored version, served from web/public/reports/<pid>/v<n>.json (archive: core/reports.py)
    anchors: dict[str, list[dict[str, Any]]] = {}
    for tx in seed["txs"]:
        if tx["kind"] != "registerQualityReport":
            continue
        pid, version = tx["project"], tx["version"]
        archived = history_path(pid, version)
        if not archived.exists():
            raise SystemExit(f"{archived} is missing; run scripts/backfill_report_history.py")
        old = json.loads(archived.read_text(encoding="utf-8"))
        (PUBLIC_REPORTS / pid).mkdir(exist_ok=True)
        shutil.copyfile(archived, PUBLIC_REPORTS / pid / archived.name)
        anchors.setdefault(pid, []).append(
            {"version": version, "tx": tx["tx"], "block": tx["block"], "report_hash": tx["report_hash"],
             "generated_at": old["generated_at"], "overall": old["overall"]["score"],
             "schema": old.get("schema", "report-v1"), "file": f"/reports/{pid}/{archived.name}"})
    for doc in _read("samples/manifest.json")["documents"]:
        pid = doc["project_id"]
        report_path = PROJECT_ROOT / "reports" / f"{pid}.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
        project: dict[str, Any] = {
            "id": pid, "name": doc["project_name"], "country": COUNTRY.get(pid),
            "category": doc["category"].replace(" - optional", ""), "doc_type": doc.get("doc_type"),
            "registry_url": doc["registry_url"], "methodology": doc["methodology"],
            "methodology_version": doc.get("methodology_version"), "reversal_risk": doc.get("reversal_risk"),
            "anchors": sorted(anchors.get(pid, []), key=lambda a: a["version"]),
            "batches": [{"key": b.key, "batch_id": "0x" + b.batch_id.hex(), "vintage": b.vintage,
                         "batch_no": b.batch_no, "first_serial": b.first_serial, "last_serial": b.last_serial,
                         "quantity": b.quantity, "lot_size": b.lot_size} for b in load_batches(pid)],
            "report": None,
            "checks": None,
        }
        checks_path = PROJECT_ROOT / "checks" / f"{pid}.json"
        if checks_path.exists():
            checks = json.loads(checks_path.read_text(encoding="utf-8"))
            coverage = next(c for c in checks["checks"] if c["id"] == "document_coverage")
            project["checks"] = {
                "offsetsdb_snapshot": checks["inputs"]["offsetsdb_snapshot"],
                "documents": [{k: d[k] for k in ("role", "pages", "tables")} for d in checks["inputs"]["documents"]],
                "missing_documents": coverage["details"]["missing"],
                "results": [{k: c[k] for k in ("id", "title", "status", "summary")} for c in checks["checks"]],
            }
        if report:
            shutil.copyfile(report_path, PUBLIC_REPORTS / report_path.name)  # byte for byte: the browser hashes it
            project["report"] = {
                "hash": hash_json(report), "generated_at": report["generated_at"],
                "document": report["document"], "documents": _documents(report["document"], doc),
                "method": report["method"], "method_hash": report["method_hash"],
                "methodology_status": report["methodology_status"], "overall": report["overall"]["score"],
                "disclaimer": report["disclaimer"], "principles": [_principle(p) for p in report["principles"]],
            }
        projects.append(project)
    projects.sort(key=lambda p: -(p["report"]["overall"] if p["report"] else -1))

    site = {
        "generated_by": "scripts/export_web_data.py",
        "network": {"name": "Sepolia", "chain_id": SEPOLIA, "contract": deployment["address"],
                    "deploy_tx": deployment["tx_hash"], "deploy_block": deployment["block"],
                    "explorer": EXPLORER},
        "methodology_statuses": table["statuses"],
        "methodology_table_version": table["table_version"],
        "evaluation": _evaluation(),
        "projects": projects,
        "buyers": _read("data/demo_buyers.json")["buyers"],
        "anonymity": {"undisclosed_share_to_2018": 0.4, "undisclosed_share_2023_2026": 17.2,
                      "snapshot": "CarbonPlan OffsetsDB, 2026-06-01", "source": "docs/anonymity_stats.md"},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(site, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(PROJECT_ROOT)}: {len(projects)} projects, "
          f"{sum(len(p['batches']) for p in projects)} batches, {len(site['buyers'])} buyers")


if __name__ == "__main__":
    main()
