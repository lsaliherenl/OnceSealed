"""End-to-end demo of the full flow on a local Anvil chain (the video storyline without the UI).

    python scripts/demo_e2e.py

Starts a throwaway Anvil node, deploys the registry, then:
  1. registers an issuance batch for a real project (VCS1477): real vintage and quantity, simulated serials
  2. anchors the published quality report (reports/VCS1477.json)
  3. a fictional buyer retires serials 1-5000; only a commitment goes on-chain
  4. a second buyer tries 4000-6000 -> rejected with AlreadyRetired
  5. the second buyer retires the adjacent range 5001-7000
  6. the auditor opens the vault, checks it against the chain, and attests
  7. the first buyer discloses their receipt; anyone verifies it; a forged receipt fails
"""

import argparse
import json
import random
import sys
import tempfile
from pathlib import Path

from core.chain import anvil
from core.chain.registry import Registry, RegistryError, connect
from core.config import PROJECT_ROOT, auditor_box_keys, chain_settings
from core.data.batches import load_batches
from core.privacy.commitment import new_salt, to_hex
from core.privacy.identity import fictional_lei
from core.privacy.vault import VaultStore
from core.service import OnceSealed


def step(n: int, title: str) -> None:
    print(f"\n[{n}] {title}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpc-url", help="use an already running anvil instead of starting one")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    proc = None
    rpc = args.rpc_url
    if rpc is None:
        port = anvil.free_port()
        proc = anvil.start_anvil(port)
        rpc = f"http://127.0.0.1:{port}"
    try:
        run(rpc)
    finally:
        if proc:
            proc.terminate()


def run(rpc: str) -> None:
    w3, accounts = connect(chain_settings("anvil", rpc))
    anvil.fund(w3, [a.address for a in accounts.values()])
    registry, deploy_tx = Registry.deploy(w3, accounts)
    print(f"RetirementRegistry deployed at {registry.address} (gas {deploy_tx.gas_used})")

    pub, priv = auditor_box_keys()
    workdir = Path(tempfile.mkdtemp(prefix="oncesealed-demo-"))
    app = OnceSealed(registry, VaultStore(workdir / "vault.sqlite"), pub, priv)
    rng = random.Random(7)
    buyer_a, buyer_b = fictional_lei(rng), fictional_lei(rng)

    step(1, "Register an issuance batch for VCS1477 (Katingan): real vintage and quantity, simulated serials")
    batch = next(b for b in load_batches("VCS1477") if b.vintage == 2020)
    tx = app.ensure_batch(batch)
    print(f"    batch {batch.key}  {batch.quantity:,} credits, serials {batch.first_serial}-{batch.last_serial}"
          f"  (gas {tx.gas_used})")

    step(2, "Anchor the published quality report")
    report = json.loads((PROJECT_ROOT / "reports" / "VCS1477.json").read_text(encoding="utf-8"))
    version, tx, report_hash = app.publish_report(report)
    print(f"    version {version}, score {report['overall']['score']}, report hash {report_hash[:18]}...")

    step(3, f"Buyer A (fictional LEI {buyer_a}) retires serials 1-5000")
    a = app.retire(batch, 1, 5000, buyer_a)
    rec = registry.get_retirement(a.retirement_id)
    print(f"    retirement #{a.retirement_id}  {a.serial_label}  (gas {a.tx.gas_used})")
    print(f"    on-chain buyer field: commitment {to_hex(rec.buyer_commitment)[:18]}...  (no name, no LEI)")
    print(f"    recorded with quality report version {rec.report_version}")
    receipt_path = workdir / "receipt_buyer_a.json"
    receipt_path.write_text(json.dumps(a.receipt, indent=2), encoding="utf-8")
    print(f"    receipt handed to buyer A: {receipt_path}")

    step(4, "Buyer B tries serials 4000-6000 (overlaps buyer A)")
    try:
        app.retire(batch, 4000, 6000, buyer_b)
        sys.exit("    ERROR: overlap was accepted")
    except RegistryError as e:
        print(f"    rejected by the contract: {e}")

    step(5, "Buyer B retires the adjacent range 5001-7000")
    b = app.retire(batch, 5001, 7000, buyer_b)
    print(f"    retirement #{b.retirement_id}  {b.serial_label}")
    print(f"    serial 5000 -> retirement #{registry.retirement_of(batch.batch_id, 5000)}, "
          f"serial 5001 -> #{registry.retirement_of(batch.batch_id, 5001)}, "
          f"serial 7001 -> {registry.retirement_of(batch.batch_id, 7001) or 'not retired'}")

    step(6, "Auditor opens buyer A's vault and attests on-chain")
    result, tx = app.audit(a.retirement_id)
    for name, ok in result.checks.items():
        print(f"    {'ok ' if ok else 'FAIL'} {name}")
    print(f"    auditor sees buyer LEI {result.payload.lei}; attestation tx gas {tx.gas_used}")
    print(f"    public status now: {app.public_record(a.retirement_id).audit.name}")

    step(7, "Buyer A discloses the receipt; anyone verifies it")
    check = app.verify_receipt(json.loads(receipt_path.read_text(encoding="utf-8")))
    print(f"    claim valid: {check.valid}  checks: {check.checks}  audit: {check.audit_status.name}")
    forged = {**a.receipt, "salt": to_hex(new_salt())}
    print(f"    forged receipt (wrong salt) valid: {app.verify_receipt(forged).valid}")
    stolen = {**b.receipt, "retirement_id": a.retirement_id}
    print(f"    buyer B's receipt pointed at A's retirement valid: {app.verify_receipt(stolen).valid}")

    print(f"\nDone. {registry.retirement_count()} retirements on-chain; vault and receipt in {workdir}")


if __name__ == "__main__":
    main()
