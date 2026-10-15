"""Deploy RetirementRegistry and grant roles; records deployments/<chain_id>.json.

    python scripts/deploy.py --network anvil      # needs a running anvil (or use demo_e2e.py)
    python scripts/deploy.py --network sepolia    # needs SEPOLIA_RPC_URL and funded role wallets
    python scripts/deploy.py --network sepolia --attach 0x...   # finish an interrupted deploy (grant roles)
"""

import argparse
import sys

from web3 import Web3

from core.chain import anvil, deployments
from core.chain.registry import Registry, TxResult, connect, load_artifact
from core.config import chain_settings

MIN_SEPOLIA_WEI = Web3.to_wei(0.003, "ether")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", choices=["anvil", "sepolia"], default="anvil")
    parser.add_argument("--rpc-url")
    parser.add_argument("--attach", metavar="ADDRESS", help="contract already deployed by the deployer wallet")
    args = parser.parse_args()

    w3, accounts = connect(chain_settings(args.network, args.rpc_url))
    chain_id = w3.eth.chain_id
    if args.network == "anvil":
        anvil.fund(w3, [a.address for a in accounts.values()])
    else:
        low = {r: a.address for r, a in accounts.items() if w3.eth.get_balance(a.address) < MIN_SEPOLIA_WEI}
        if low:
            sys.exit(f"these role wallets need Sepolia ETH first (scripts/fund_roles.py): {low}")

    if args.attach:
        reg = Registry(w3, args.attach, accounts)
        tx = _deploy_tx(w3, reg.address, accounts["deployer"].address)
        reg.grant_roles()
    else:
        reg, tx = Registry.deploy(w3, accounts)
    record = deployments.save(chain_id, args.network, reg.address, tx.tx_hash, tx.block_number,
                              {r: a.address for r, a in accounts.items()}, load_artifact()["compiler"], tx.gas_used)
    print(f"RetirementRegistry deployed on {args.network} (chain {chain_id}) at {reg.address}")
    print(f"tx {tx.tx_hash}, block {tx.block_number}, gas {tx.gas_used}")
    print(f"-> deployments/{chain_id}.json  roles: {record['roles']}")


def _deploy_tx(w3: Web3, address: str, deployer: str) -> TxResult:
    """Find the creation transaction of `address` among the deployer's transactions (nonce search)."""
    from eth_utils import keccak, to_checksum_address
    import rlp

    for nonce in range(w3.eth.get_transaction_count(deployer) - 1, -1, -1):
        created = to_checksum_address(keccak(rlp.encode([bytes.fromhex(deployer[2:]), nonce]))[12:])
        if created == Web3.to_checksum_address(address):
            break
    else:
        sys.exit(f"{address} was not created by {deployer}")
    # scan recent blocks for that nonce
    head = w3.eth.block_number
    for b in range(head, head - 2000, -1):
        for t in w3.eth.get_block(b, full_transactions=True)["transactions"]:
            if t["from"] == deployer and t["nonce"] == nonce:
                r = w3.eth.get_transaction_receipt(t["hash"])
                return TxResult("0x" + bytes(t["hash"]).hex(), r["blockNumber"], r["gasUsed"], r)
    sys.exit("creation transaction not found in the last 2,000 blocks")


if __name__ == "__main__":
    main()
