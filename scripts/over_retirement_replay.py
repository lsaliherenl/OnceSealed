"""D4: replay real OffsetsDB histories where retirements exceed issuance, through the contract on Anvil.

    python scripts/over_retirement_replay.py

For each project-vintage whose retired quantity exceeds its issued quantity, register one batch with
serials 1..issued and replay the retirements chronologically as consecutive serial ranges. Any
retirement that would go past the issued serials is rejected by the contract (InvalidRange).
Writes data/derived/over_retirement.json.

Caveat: an excess in OffsetsDB is not proof of real double counting; it can also come from vintage
labelling or data-entry differences in the registries.
"""

import json
import math
import os
import sys

from eth_account import Account
from web3 import Web3

from core.chain import anvil
from core.chain.registry import Registry, RegistryError, connect
from core.config import PROJECT_ROOT, ROLES, ChainSettings
from core.data import offsetsdb


def cases():
    c = offsetsdb.credits()
    c = c[c["vintage"].notna()]
    g = c.groupby(["project_id", "vintage", "transaction_type"])["quantity"].sum().unstack(fill_value=0)
    g = g[(g.get("issuance", 0) > 0) & (g["retirement"] > g["issuance"] * 1.0001)]
    for (pid, vintage), row in g.iterrows():
        ret = c[(c["project_id"] == pid) & (c["vintage"] == vintage) & (c["transaction_type"] == "retirement")]
        yield pid, int(vintage), row["issuance"], ret.sort_values("transaction_date")["quantity"].tolist()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    port = anvil.free_port()
    proc = anvil.start_anvil(port)
    results = []
    try:
        keys = {role: "0x" + Account.create().key.hex().removeprefix("0x") for role in ROLES}
        w3, accounts = connect(ChainSettings("anvil", f"http://127.0.0.1:{port}", keys))
        anvil.fund(w3, [a.address for a in accounts.values()])
        reg, _ = Registry.deploy(w3, accounts)
        for pid, vintage, issued, quantities in cases():
            issued_units = math.floor(issued)  # serials are whole credits
            batch_id = Web3.keccak(text=f"{pid}|{vintage}|over-retirement-check")
            reg.register_batch(batch_id, Web3.keccak(text=pid), 1, issued_units)
            cursor, accepted, rejected, rejected_t, first_rejected = 0, 0, 0, 0, None
            for i, q in enumerate(quantities, start=1):
                units = max(1, math.ceil(q))
                try:
                    reg.retire(batch_id, cursor + 1, cursor + units, os.urandom(32), os.urandom(32))
                    cursor += units
                    accepted += 1
                except RegistryError as e:
                    if e.name != "InvalidRange":
                        raise
                    rejected += 1
                    rejected_t += units
                    first_rejected = first_rejected or i
            results.append({"project_id": pid, "vintage": vintage, "issued": issued, "retired": sum(quantities),
                            "excess": sum(quantities) - issued, "retirements": len(quantities),
                            "accepted": accepted, "rejected": rejected, "rejected_tonnes": rejected_t,
                            "first_rejected_retirement": first_rejected})
            print(f"{pid:8s} {vintage}  issued {issued:>11,.0f}  retired {sum(quantities):>11,.0f}  "
                  f"-> rejected {rejected:3d} of {len(quantities):4d} retirements ({rejected_t:,} t)")
    finally:
        proc.terminate()
    total = {"cases": len(results), "retirements": sum(r["retirements"] for r in results),
             "rejected": sum(r["rejected"] for r in results), "excess_tonnes": sum(r["excess"] for r in results),
             "rejected_tonnes": sum(r["rejected_tonnes"] for r in results)}
    print(f"\n{total}")
    out = PROJECT_ROOT / "data" / "derived" / "over_retirement.json"
    out.write_text(json.dumps({"snapshot": offsetsdb.snapshot_date(), "total": total, "cases": results}, indent=2)
                   + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
