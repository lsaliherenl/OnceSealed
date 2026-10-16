"""Export the public data the web UI renders into web/src/data/site.json.

The project pages are static: they show the published reports in reports/, the methodology table,
the simulated issuance batches and the Sepolia deployment, all read here at build time. Each report
carries the hash the contract should hold (`hash_json` of the published file), so the browser can
compare it with `latestReport` on-chain without trusting this file. Run after a report, data check, batch or
deployment changes:

    python scripts/export_web_data.py
"""

import json
from typing import Any

from core.config import PROJECT_ROOT
from core.data.batches import load_batches
from core.hashing import hash_json

OUT = PROJECT_ROOT / "web" / "src" / "data" / "site.json"
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
        "quotes": [{"text": q["text"], "page": q["page"], "verification": q.get("verification")}
                   for q in p.get("quotes", [])],
    }


def main() -> None:
    deployment = _read(f"deployments/{SEPOLIA}.json")
    seed = _read(f"deployments/{SEPOLIA}-seed.json")
    if seed["contract"].lower() != deployment["address"].lower():
        raise SystemExit("seed log is for another contract; re-run scripts/seed_sepolia.py first")
    table = _read("core/ai/methodology_status.json")

    anchors: dict[str, list[dict[str, Any]]] = {}
    for tx in seed["txs"]:
        if tx["kind"] == "registerQualityReport":
            anchors.setdefault(tx["project"], []).append(
                {"version": tx["version"], "tx": tx["tx"], "block": tx["block"], "report_hash": tx["report_hash"]})

    projects = []
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
            project["report"] = {
                "hash": hash_json(report), "generated_at": report["generated_at"],
                "document": report["document"], "method": report["method"], "method_hash": report["method_hash"],
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
