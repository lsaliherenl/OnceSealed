"""D2 scale test: replay a real OffsetsDB retirement history through RetirementRegistry on Anvil.

    python scripts/scale_replay.py --project VCS1477 --vintage 2020
    python scripts/scale_replay.py --project VCS766 --vintage 2009 --max 12000

Each real retirement (chronological) becomes the next serial range in one issuance batch.
Records gas and latency per transaction until the history ends or a retirement no longer
fits in a block. Writes data/derived/scale/<project>-<vintage>-<variant>.csv.
"""

import argparse
import csv
import os
import sys
import time

from web3 import Web3

from core.chain import anvil
from core.chain.registry import Registry, connect, load_artifact
from core.config import PROJECT_ROOT, ROLES, ChainSettings
from core.data import offsetsdb
from eth_account import Account

OUT_DIR = PROJECT_ROOT / "data" / "derived" / "scale"


def history(project: str, vintage: int) -> tuple[int, list[int]]:
    c = offsetsdb.credits()
    sel = c[(c["project_id"] == project) & (c["vintage"] == vintage)]
    issued = int(sel.loc[sel["transaction_type"] == "issuance", "quantity"].sum())
    ret = sel[sel["transaction_type"] == "retirement"].sort_values("transaction_date")
    return issued, [int(q) for q in ret["quantity"] if q >= 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="VCS1477")
    parser.add_argument("--vintage", type=int, default=2020)
    parser.add_argument("--max", type=int, default=None, help="stop after this many retirements")
    parser.add_argument("--block-gas", type=int, default=36_000_000, help="block gas limit to emulate")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    issued, quantities = history(args.project, args.vintage)
    if args.max:
        quantities = quantities[: args.max]
    print(f"{args.project} vintage {args.vintage}: issued {issued:,}, {len(quantities):,} retirements to replay")

    port = anvil.free_port()
    # Blocks are made huge so the EIP-1559 base fee never climbs (a test-chain artefact that would drain the
    # test account); the real block limit is enforced per transaction through its gas cap (args.block_gas).
    proc = anvil.start_anvil(port, extra_args=["--gas-limit", "1000000000"])
    try:
        keys = {role: "0x" + Account.create().key.hex().removeprefix("0x") for role in ROLES}
        w3, accounts = connect(ChainSettings("anvil", f"http://127.0.0.1:{port}", keys))
        anvil.fund(w3, [a.address for a in accounts.values()])
        reg, _ = Registry.deploy(w3, accounts)
        variant = "hinted" if reg.uses_hints else "linear"
        batch_id = Web3.keccak(text=f"{args.project}|{args.vintage}|replay")
        reg.register_batch(batch_id, Web3.keccak(text=args.project), 1, max(issued, sum(quantities)))

        op = accounts["operator"]
        nonce = w3.eth.get_transaction_count(op.address)
        cursor, prev_id = 0, 0
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / f"{args.project}-{args.vintage}-{variant}.csv"
        f = open(out, "w", newline="", encoding="utf-8")  # written row by row: a crash keeps the data so far
        writer = csv.DictWriter(f, fieldnames=["n", "start", "end", "gas_used", "ok", "latency_ms"])
        writer.writeheader()
        t_start = time.time()
        for i, q in enumerate(quantities, start=1):
            start, end = cursor + 1, cursor + q
            fn = reg.retire_fn(batch_id, start, end, os.urandom(32), os.urandom(32), prev_hint=prev_id)
            # Full blocks push the EIP-1559 base fee up, so price each tx from the latest block.
            base_fee = w3.eth.get_block("latest")["baseFeePerGas"]
            tx = fn.build_transaction({"from": op.address, "nonce": nonce, "gas": args.block_gas,
                                       "maxFeePerGas": 2 * base_fee + 1, "maxPriorityFeePerGas": 0})
            t0 = time.perf_counter()
            receipt = w3.eth.wait_for_transaction_receipt(
                w3.eth.send_raw_transaction(op.sign_transaction(tx).raw_transaction))
            dt = time.perf_counter() - t0
            nonce += 1
            ok = receipt["status"] == 1
            writer.writerow({"n": i, "start": start, "end": end, "gas_used": receipt["gasUsed"], "ok": int(ok),
                             "latency_ms": round(dt * 1000, 2)})
            f.flush()
            if not ok:
                print(f"  retirement #{i} FAILED (gas used {receipt['gasUsed']:,} of {args.block_gas:,})")
                break
            prev_id = i  # replay is chronological and sequential, so the previous retirement is the neighbour
            cursor = end
            if i % 500 == 0 or i == len(quantities):
                print(f"  {i:6,} retirements  last gas {receipt['gasUsed']:>11,}  ({time.time() - t_start:.0f}s)")
        f.close()
        print(f"variant={variant} artifact={load_artifact()['compiler']} -> {out.relative_to(PROJECT_ROOT)}")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
