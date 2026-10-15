"""Scale check for lookups: the contract's list-walking views vs the client's CreditRetired event index.

    python scripts/index_benchmark.py 1000 5000

For a free-range batch with N retirements on a throwaway Anvil chain, prints the eth_call gas of the
contract's hintFor / retirementOf (grows with N; public RPCs typically cap eth_call at 50M gas) and the
time to build the event index from logs and answer one lookup (core/chain/registry.py, _RangeIndex).
"""

import os
import sys
import time

from eth_account import Account

from core.chain import anvil
from core.chain.registry import Registry, connect
from core.config import ROLES, ChainSettings


def bench(n: int) -> None:
    port = anvil.free_port()
    proc = anvil.start_anvil(port, ["--gas-limit", "1000000000"])
    try:
        keys = {r: "0x" + Account.create().key.hex().removeprefix("0x") for r in ROLES}
        w3, accounts = connect(ChainSettings("anvil", f"http://127.0.0.1:{port}", keys))
        anvil.fund(w3, [a.address for a in accounts.values()])
        reg, _ = Registry.deploy(w3, accounts)
        batch = os.urandom(32)
        reg.register_batch(batch, os.urandom(32), 1, 10 * n)
        op = accounts["operator"]
        nonce = w3.eth.get_transaction_count(op.address)
        tx_hash = None
        for i in range(n):  # chronological ranges, so the predecessor is always the previous retirement
            fn = reg.retire_fn(batch, 10 * i + 1, 10 * i + 10, os.urandom(32), os.urandom(32), i)
            tx = fn.build_transaction({"from": op.address, "nonce": nonce + i, "gas": 400_000})
            tx_hash = w3.eth.send_raw_transaction(op.sign_transaction(tx).raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)

        last = 10 * n
        gas_hint = reg.contract.functions.hintFor(batch, last).estimate_gas()
        gas_lookup = reg.contract.functions.retirementOf(batch, last).estimate_gas()
        fresh = Registry(w3, reg.address, accounts)  # no cached index: built from logs here
        t = time.perf_counter()
        hint = fresh.hint_for(batch, last)
        build_s = time.perf_counter() - t
        t = time.perf_counter()
        fresh.retirement_of(batch, last)
        lookup_ms = (time.perf_counter() - t) * 1000
        assert hint == reg.contract.functions.hintFor(batch, last).call()
        print(f"{n:,} retirements: contract hintFor {gas_hint:,} gas, retirementOf {gas_lookup:,} gas per eth_call | "
              f"event index built in {build_s:.2f} s, then {lookup_ms:.2f} ms per lookup")
    finally:
        proc.terminate()


if __name__ == "__main__":
    for arg in sys.argv[1:] or ["1000"]:
        bench(int(arg))
