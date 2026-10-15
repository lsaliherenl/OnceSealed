"""Record where the registry is deployed: deployments/<chain_id>.json.

Sepolia deployments are committed (judges can find the contract); local Anvil ones are not.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT

DEPLOYMENTS_DIR = PROJECT_ROOT / "deployments"


def path_for(chain_id: int) -> Path:
    return DEPLOYMENTS_DIR / f"{chain_id}.json"


def save(chain_id: int, network: str, address: str, tx_hash: str, block: int,
         roles: dict[str, str], artifact_compiler: str | None, gas_used: int | None = None) -> dict[str, Any]:
    record = {
        "network": network, "chain_id": chain_id, "address": address, "tx_hash": tx_hash, "block": block,
        "gas_used": gas_used, "roles": roles, "compiler": artifact_compiler,
        "deployed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    old = load(chain_id)
    if old and old["address"] != address:  # keep earlier contract versions findable
        record["previous"] = [*old.get("previous", []), {k: old.get(k) for k in ("address", "tx_hash", "deployed_at")}]
    DEPLOYMENTS_DIR.mkdir(exist_ok=True)
    path_for(chain_id).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def load(chain_id: int) -> dict[str, Any] | None:
    p = path_for(chain_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
