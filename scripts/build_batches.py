"""Build simulated issuance batches for the demo projects from real OffsetsDB issuance records.

    python scripts/build_batches.py

Each OffsetsDB issuance record becomes one batch: real project, vintage, date and quantity;
simulated serial numbers 1..quantity. Writes data/batches.json (committed, so the app runs
without the raw OffsetsDB snapshot).
"""

import json

from core.config import PROJECT_ROOT
from core.data import offsetsdb
from core.data.batches import IssuanceBatch


def main() -> None:
    manifest = json.loads((PROJECT_ROOT / "samples" / "manifest.json").read_text(encoding="utf-8"))
    project_ids = [d["project_id"] for d in manifest["documents"]]
    c = offsetsdb.credits()
    iss = c[(c["transaction_type"] == "issuance") & c["project_id"].isin(project_ids)]
    iss = iss.sort_values(["project_id", "vintage", "transaction_date", "quantity"])

    batches = []
    for (pid, vintage), group in iss.groupby(["project_id", "vintage"], sort=True):
        for n, row in enumerate(group.itertuples(), start=1):
            b = IssuanceBatch(pid, int(vintage), n, 1, int(row.quantity))
            batches.append({
                "key": b.key, "batch_id": "0x" + b.batch_id.hex(), "project_id": pid, "vintage": int(vintage),
                "batch_no": n, "first_serial": b.first_serial, "last_serial": b.last_serial,
                "quantity": b.quantity, "issued_on": row.transaction_date.date().isoformat(),
            })
    out = {
        "note": "Simulated serial ranges sized from real OffsetsDB issuance records. Not real Verra serial numbers.",
        "source": f"CarbonPlan OffsetsDB snapshot {offsetsdb.snapshot_date()}",
        "batches": batches,
    }
    path = PROJECT_ROOT / "data" / "batches.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    per = {p: sum(1 for b in batches if b["project_id"] == p) for p in project_ids}
    print(f"wrote {path.relative_to(PROJECT_ROOT)}: {len(batches)} batches {per}")


if __name__ == "__main__":
    main()
