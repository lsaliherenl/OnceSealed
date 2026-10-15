"""D3 / threat T12: how identifying is on-chain metadata (project, quantity, time)? OffsetsDB measurement.

    python scripts/linkability_stats.py

Prints the two tables used in docs/threat_model.md and writes data/derived/linkability.json.
"""

import json
import sys

import pandas as pd

from core.config import PROJECT_ROOT
from core.data import offsetsdb

KEYS = {
    "project + quantity": ["project_id", "quantity"],
    "project + quantity + month": ["project_id", "quantity", "month"],
    "project + quantity + day": ["project_id", "quantity", "day"],
    "project + day": ["project_id", "day"],
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    c = offsetsdb.credits()
    r = c[c["transaction_type"] == "retirement"][["project_id", "quantity", "transaction_date"]].copy()
    ts = pd.to_datetime(r["transaction_date"], utc=True)
    r["day"] = ts.dt.date
    r["month"] = ts.dt.strftime("%Y-%m")
    total = r["quantity"].sum()

    unique = {}
    for name, cols in KEYS.items():
        is_unique = r.groupby(cols)["quantity"].transform("size") == 1
        unique[name] = {"records": float(is_unique.mean()), "tonnes": float(r.loc[is_unique, "quantity"].sum() / total)}
        print(f"{name:28s} unique records {unique[name]['records']:6.1%}   tonnes {unique[name]['tonnes']:6.1%}")

    lots = {}
    for lot in (100, 1_000, 10_000):
        full = (r["quantity"] // lot) * lot
        per_project = (r["quantity"] // lot).groupby(r["project_id"]).sum()
        lots[lot] = {"tonnes_in_lots": float(full.sum() / total),
                     "tonnes_in_remainders": float((r["quantity"] - full).sum() / total),
                     "median_anonymity_set": int(per_project[per_project > 0].median())}
        print(f"lot {lot:>6,} t: {lots[lot]['tonnes_in_lots']:6.1%} in lots, "
              f"{lots[lot]['tonnes_in_remainders']:5.1%} remainders, median set {lots[lot]['median_anonymity_set']:,}")

    # Lots hide the amount, but a buyer's lots still appear together in time. Model: the operator publishes
    # all lots of a project once per epoch, shuffled. An observer then knows a buyer's lots are among the
    # lots of that project and epoch, but not which ones: the anonymity set is the number of purchases
    # (OffsetsDB retirement records) that had at least one lot in that project-epoch. 1 = fully exposed.
    lot = 1_000
    r["lots"] = r["quantity"] // lot
    with_lots = r[r["lots"] > 0].copy()
    lot_tonnes = float((with_lots["lots"] * lot).sum())
    epochs = {}
    for name, freq in (("day", "D"), ("week", "W"), ("month", "M"), ("quarter", "Q")):
        period = ts.loc[with_lots.index].dt.tz_localize(None).dt.to_period(freq)
        k = with_lots.groupby([with_lots["project_id"], period])["lots"].transform("size")
        w = with_lots["lots"] * lot
        epochs[name] = {"median_set": float(k.median()),
                        "tonnes_exposed_k1": float(w[k == 1].sum() / lot_tonnes),
                        "tonnes_k_ge_5": float(w[k >= 5].sum() / lot_tonnes),
                        "tonnes_k_ge_10": float(w[k >= 10].sum() / lot_tonnes)}
        e = epochs[name]
        print(f"lots of {lot:,} t, published per {name:7s}: median set {e['median_set']:5.0f}; tonnes alone "
              f"{e['tonnes_exposed_k1']:6.1%}, in sets of >=5 purchases {e['tonnes_k_ge_5']:6.1%}, "
              f">=10 {e['tonnes_k_ge_10']:6.1%}")

    out = {"snapshot": offsetsdb.snapshot_date(), "retirements": int(len(r)), "unique": unique, "lots": lots,
           "lots_with_epochs": {"lot_size": lot, "note": "anonymity set = purchases with lots in the same "
                                "project and epoch; share of tonnes retired in whole lots", "epochs": epochs}}
    path = PROJECT_ROOT / "data" / "derived" / "linkability.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
