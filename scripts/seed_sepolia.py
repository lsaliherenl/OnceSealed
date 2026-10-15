"""Put the public demo state on Sepolia: anchored reports, issuance batches, one audited retirement.

    python scripts/seed_sepolia.py            # idempotent: skips reports and batches already on-chain

Writes deployments/11155111-seed.json with every transaction (Etherscan links) and its gas, so the
README can quote real Sepolia gas next to the Anvil measurements. The buyer is fictional
(data/demo_buyers.json) and the serials are simulated; the receipt goes to data/receipts/ (gitignored).
"""

import json
import sys

from core.chain import deployments
from core.chain.registry import Registry, connect
from core.config import PROJECT_ROOT, auditor_box_keys, chain_settings
from core.data.batches import load_batches
from core.privacy.identity import project_id
from core.privacy.vault import VaultStore
from core.service import OnceSealed

SEPOLIA = 11155111
DEMO_PROJECTS = ("VCS1477", "VCS1851", "VCS138", "VCS2505")


def link(tx_hash: str) -> str:
    return f"https://sepolia.etherscan.io/tx/{tx_hash}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    w3, accounts = connect(chain_settings("sepolia"))
    if w3.eth.chain_id != SEPOLIA:
        sys.exit("not Sepolia")
    record = deployments.load(SEPOLIA)
    registry = Registry(w3, record["address"], accounts)
    public, private = auditor_box_keys()
    svc = OnceSealed(registry, VaultStore(PROJECT_ROOT / "data" / "vault" / f"{SEPOLIA}.sqlite"), public, private)
    out_path = PROJECT_ROOT / "deployments" / f"{SEPOLIA}-seed.json"
    log = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {"txs": []}

    def note(kind: str, tx, **extra) -> None:
        log["txs"].append({"kind": kind, "tx": tx.tx_hash, "block": tx.block_number, "gas": tx.gas_used, **extra})
        out_path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
        print(f"  {kind:22s} gas {tx.gas_used:>10,}  {link(tx.tx_hash)}")

    print("quality reports")
    for pid in DEMO_PROJECTS:
        if registry.report_count(project_id(pid)) > 0:
            print(f"  {pid}: already anchored")
            continue
        report = json.loads((PROJECT_ROOT / "reports" / f"{pid}.json").read_text(encoding="utf-8"))
        version, tx, report_hash = svc.publish_report(report)
        note("registerQualityReport", tx, project=pid, version=version, report_hash=report_hash)

    print("issuance batches (first batch of each project; simulated serials)")
    batches = {pid: load_batches(pid)[0] for pid in DEMO_PROJECTS}
    for pid, b in batches.items():
        tx = svc.ensure_batch(b)
        if tx is None:
            print(f"  {b.key}: already registered")
        else:
            note("registerBatch", tx, batch=b.key, serials=[b.first_serial, b.last_serial])

    if any(t["kind"] == "retire" for t in log["txs"]):
        print("demo retirement already done")
        return
    print("one retirement by a fictional buyer, then the auditor's attestation")
    buyer = json.loads((PROJECT_ROOT / "data" / "demo_buyers.json").read_text(encoding="utf-8"))["buyers"][0]
    batch = batches["VCS1477"]
    outcome = svc.retire(batch, 1, 1000, buyer["lei"])
    note("retire", outcome.tx, retirement_id=outcome.retirement_id, batch=batch.key, range=[1, 1000])
    receipts = PROJECT_ROOT / "data" / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    (receipts / f"sepolia-{outcome.retirement_id}.json").write_text(json.dumps(outcome.receipt, indent=2) + "\n",
                                                                    encoding="utf-8")
    result, tx = svc.audit(outcome.retirement_id)
    print(f"  audit checks: {result.checks}")
    if tx:
        note("attestRetirement", tx, retirement_id=outcome.retirement_id, valid=result.valid)
    check = svc.verify_receipt(outcome.receipt)
    print(f"  receipt verifies against Sepolia: {check.valid}")


if __name__ == "__main__":
    main()
