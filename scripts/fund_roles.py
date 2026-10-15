"""Top up the assessor, operator and auditor wallets with Sepolia test ETH from the deployer wallet.

Run it yourself (it sends transactions):

    python scripts/fund_roles.py              # shows balances and what would be sent
    python scripts/fund_roles.py --send       # actually sends

Sepolia ETH has no monetary value; still, check the plan it prints before using --send.
"""

import argparse
import sys

from web3 import Web3

from core.chain.registry import connect
from core.config import chain_settings

TARGET = Web3.to_wei(0.008, "ether")  # enough for hundreds of demo transactions per role


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()

    w3, accounts = connect(chain_settings("sepolia"))
    if w3.eth.chain_id != 11155111:
        sys.exit(f"not Sepolia (chain id {w3.eth.chain_id})")
    deployer = accounts["deployer"]
    print(f"deployer {deployer.address}: {Web3.from_wei(w3.eth.get_balance(deployer.address), 'ether')} ETH")

    plan = []
    for role in ("assessor", "operator", "auditor"):
        addr = accounts[role].address
        bal = w3.eth.get_balance(addr)
        need = max(0, TARGET - bal)
        plan.append((role, addr, need))
        gas = w3.eth.estimate_gas({"from": deployer.address, "to": addr, "value": need}) if need else 0
        print(f"{role:9s} {addr}: {Web3.from_wei(bal, 'ether')} ETH -> send {Web3.from_wei(need, 'ether')} ETH "
              f"(estimated gas {gas:,})")

    if not args.send:
        print("\ndry run; add --send to transfer")
        return
    nonce = w3.eth.get_transaction_count(deployer.address, "pending")
    for role, addr, need in plan:
        if need == 0:
            continue
        # Never hard-code 21,000: Sepolia now charges extra gas for creating a new (empty) account,
        # so a plain transfer to a fresh wallet needs ~207k gas and fails out of gas at 21k.
        gas = w3.eth.estimate_gas({"from": deployer.address, "to": addr, "value": need})
        tx = {"to": addr, "value": need, "nonce": nonce, "gas": gas * 12 // 10, "chainId": 11155111,
              "maxFeePerGas": 2 * w3.eth.get_block("latest")["baseFeePerGas"] + w3.to_wei(1, "gwei"),
              "maxPriorityFeePerGas": w3.to_wei(1, "gwei")}
        h = w3.eth.send_raw_transaction(deployer.sign_transaction(tx).raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(h, timeout=300)
        url = f"https://sepolia.etherscan.io/tx/0x{bytes(h).hex()}"
        if receipt["status"] != 1:
            sys.exit(f"transfer to {role} FAILED (gas used {receipt['gasUsed']}): {url}")
        print(f"sent {Web3.from_wei(need, 'ether')} ETH to {role} (gas {receipt['gasUsed']:,}): {url}")
        nonce += 1


if __name__ == "__main__":
    main()
