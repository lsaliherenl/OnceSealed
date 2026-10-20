"""Published quality reports and the archive of every version anchored on-chain.

reports/<project>.json is the latest published report; reports/history/<project>/v<n>.json is the exact file
anchored as version n (its keccak256 over canonical JSON is the hash the contract stores). A retirement records
the report version current when it happened, so old versions stay readable after a report is replaced.
"""

import json
import shutil
from pathlib import Path

from core.config import PROJECT_ROOT

REPORTS = PROJECT_ROOT / "reports"
HISTORY = REPORTS / "history"
SEPOLIA_SEED = PROJECT_ROOT / "deployments" / "11155111-seed.json"


def history_path(project_id: str, version: int) -> Path:
    return HISTORY / project_id / f"v{version}.json"


def archive(project_id: str, version: int) -> Path:
    """Copy the published report, just anchored as `version`, into the archive (byte for byte)."""
    path = history_path(project_id, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPORTS / f"{project_id}.json", path)
    return path


def anchored_versions(seed: Path = SEPOLIA_SEED) -> dict[str, list[tuple[int, str]]]:
    """{project: [(version, report_hash), ...]} from the Sepolia transaction log."""
    out: dict[str, list[tuple[int, str]]] = {}
    for tx in json.loads(seed.read_text(encoding="utf-8"))["txs"]:
        if tx["kind"] == "registerQualityReport":
            out.setdefault(tx["project"], []).append((tx["version"], tx["report_hash"]))
    return {p: sorted(v) for p, v in out.items()}
