"""Uvicorn entry point, configured from .env.

    uvicorn api.server:app --reload                                 # local Anvil (start `anvil` first)
    ONCESEALED_NETWORK=sepolia uvicorn api.server:app               # Sepolia, uses deployments/11155111.json

On Anvil the registry is (re)deployed automatically when no live deployment is found,
because restarting Anvil wipes the chain.
"""

import os

from core.chain import anvil, deployments
from core.chain.registry import Registry, connect, load_artifact
from core.config import PROJECT_ROOT, auditor_box_keys, chain_settings
from core.privacy.vault import VaultStore
from core.service import OnceSealed

from api.app import create_app


def build():
    network = os.environ.get("ONCESEALED_NETWORK", "anvil")
    w3, accounts = connect(chain_settings(network, os.environ.get("ONCESEALED_RPC_URL")))
    chain_id = w3.eth.chain_id
    record = deployments.load(chain_id)
    live = record is not None and len(w3.eth.get_code(record["address"])) > 0
    if live:
        registry = Registry(w3, record["address"], accounts)
    elif network == "anvil":
        anvil.fund(w3, [a.address for a in accounts.values()])
        registry, tx = Registry.deploy(w3, accounts)
        deployments.save(chain_id, network, registry.address, tx.tx_hash, tx.block_number,
                         {r: a.address for r, a in accounts.items()}, load_artifact()["compiler"])
    else:
        raise RuntimeError(f"no deployment for chain {chain_id}; run scripts/deploy.py --network {network}")

    public, private = auditor_box_keys()
    service = OnceSealed(registry, VaultStore(PROJECT_ROOT / "data" / "vault" / f"{chain_id}.sqlite"), public, private)
    tokens = {"operator": os.environ.get("OPERATOR_API_TOKEN", ""), "auditor": os.environ.get("AUDITOR_API_TOKEN", "")}
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    return create_app(service, network, tokens, origins)


app = build()
