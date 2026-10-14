"""Deploy RetirementRegistry and grant roles; records deployments/<chain_id>.json.

    python scripts/deploy.py --network anvil      # needs a running anvil (or use demo_e2e.py)
    python scripts/deploy.py --network sepolia    # needs SEPOLIA_RPC_URL and funded role wallets
"""

import argparse
import sys

from web3 import Web3

from core.chain import anvil, deployments
from core.chain.registry import Registry, connect, load_artifact
from core.config import chain_settings

MIN_SEPOLIA_WEI = Web3.to_wei(0.003, "ether")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", choices=["anvil", "sepolia"], default="anvil")
    parser.add_argument("--rpc-url")
    args = parser.parse_args()

    w3, accounts = connect(chain_settings(args.network, args.rpc_url))
    chain_id = w3.eth.chain_id
    if args.network == "anvil":
        anvil.fund(w3, [a.address for a in accounts.values()])
    else:
        low = {r: a.address for r, a in accounts.items() if w3.eth.get_balance(a.address) < MIN_SEPOLIA_WEI}
        if low:
            sys.exit(f"these role wallets need Sepolia ETH first (scripts/fund_roles.py): {low}")

    reg, tx = Registry.deploy(w3, accounts)
    record = deployments.save(chain_id, args.network, reg.address, tx.tx_hash, tx.block_number,
                              {r: a.address for r, a in accounts.items()}, load_artifact()["compiler"])
    print(f"RetirementRegistry deployed on {args.network} (chain {chain_id}) at {reg.address}")
    print(f"tx {tx.tx_hash}, block {tx.block_number}, gas {tx.gas_used}")
    print(f"-> deployments/{chain_id}.json  roles: {record['roles']}")


if __name__ == "__main__":
    main()
