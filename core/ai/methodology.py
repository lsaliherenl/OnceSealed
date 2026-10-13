"""Layer 1: deterministic ICVCM methodology status lookup (no AI)."""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

TABLE_PATH = Path(__file__).with_name("methodology_status.json")


@lru_cache(maxsize=1)
def load_table() -> dict[str, Any]:
    return json.loads(TABLE_PATH.read_text(encoding="utf-8"))


def _version_number(version: str | None) -> float | None:
    m = re.match(r"\s*(\d+(?:\.\d+)?)", version or "")
    return float(m.group(1)) if m else None


def methodology_status(code: str, version: str | None = None) -> dict[str, Any]:
    """Return the table entry for a methodology code/version, or an 'unknown' record."""
    table = load_table()
    code = code.strip().upper()
    for entry in table["methodologies"]:
        if entry["code"] != code:
            continue
        lo, hi = entry.get("min_version"), entry.get("max_version")
        v = _version_number(version)
        if lo is not None and (v is None or not lo <= v <= hi):
            return {
                "code": code, "version": version, "status": "not_ccp_approved",
                "summary": f"Only versions {entry['versions']} of {code} are covered by the ICVCM decision.",
                "sources": entry["sources"], "table_version": table["table_version"],
            }
        return {"code": code, "version": version, **{k: entry[k] for k in ("status", "summary", "sources")},
                "table_version": table["table_version"]}
    return {"code": code, "version": version, "status": "unknown",
            "summary": "No ICVCM decision recorded for this methodology.", "sources": [],
            "table_version": table["table_version"]}
