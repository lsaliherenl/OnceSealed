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
         roles: dict[str, str], artifact_compiler: str | None) -> dict[str, Any]:
    record = {
        "network": network, "chain_id": chain_id, "address": address, "tx_hash": tx_hash, "block": block,
        "roles": roles, "compiler": artifact_compiler,
        "deployed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    DEPLOYMENTS_DIR.mkdir(exist_ok=True)
    path_for(chain_id).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def load(chain_id: int) -> dict[str, Any] | None:
    p = path_for(chain_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
