"""Verify the deployed RetirementRegistry source on Etherscan (Sepolia).

    python scripts/verify_etherscan.py            # address and constructor args from deployments/11155111.json

Uses `forge verify-contract --show-standard-json-input` for the exact compiler input, then submits it
to the Etherscan v2 API (forge's own submission can time out on slow connections). Needs
ETHERSCAN_API_KEY in .env and Foundry in ~/.foundry/bin.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values
from eth_abi import encode

from core.chain import deployments
from core.chain.registry import DEFAULT_ADMIN_DELAY, load_artifact
from core.config import PROJECT_ROOT

API = "https://api.etherscan.io/v2/api"
CHAIN_ID = 11155111
FORGE = Path.home() / ".foundry" / "bin" / "forge"


def main() -> None:
    record = deployments.load(CHAIN_ID)
    address, admin = record["address"], record["roles"]["deployer"]
    ctor = encode(["uint48", "address"], [DEFAULT_ADMIN_DELAY, admin]).hex()
    std = subprocess.run([str(FORGE), "verify-contract", address, "src/RetirementRegistry.sol:RetirementRegistry",
                          "--chain", "sepolia", "--constructor-args", "0x" + ctor, "--show-standard-json-input"],
                         cwd=PROJECT_ROOT / "contracts", capture_output=True, encoding="utf-8", check=True).stdout
    json.loads(std)  # fail early if forge printed something else
    key = dotenv_values(PROJECT_ROOT / ".env").get("ETHERSCAN_API_KEY")
    if not key:
        sys.exit("ETHERSCAN_API_KEY is empty in .env")
    client = httpx.Client(timeout=120)
    params = {"chainid": CHAIN_ID, "apikey": key, "module": "contract"}
    for _ in range(10):  # right after a deploy Etherscan may not have indexed the contract yet
        res = client.post(API, params={"chainid": CHAIN_ID}, data={
            "apikey": key, "module": "contract", "action": "verifysourcecode", "contractaddress": address,
            "sourceCode": std, "codeformat": "solidity-standard-json-input",
            "contractname": "src/RetirementRegistry.sol:RetirementRegistry",
            "compilerversion": "v" + load_artifact()["compiler"], "constructorArguements": ctor}).json()
        if "Unable to locate ContractCode" not in str(res.get("result")):
            break
        print("Etherscan has not indexed the contract yet; retrying in 20 s")
        time.sleep(20)
    if res.get("status") != "1":
        sys.exit(f"submission refused: {res.get('result')}")
    for _ in range(20):
        time.sleep(8)
        status = client.get(API, params={**params, "action": "checkverifystatus", "guid": res["result"]}).json()
        print(status.get("result"))
        if "Pending" not in str(status.get("result")):
            break
    print(f"https://sepolia.etherscan.io/address/{address}#code")


if __name__ == "__main__":
    main()
