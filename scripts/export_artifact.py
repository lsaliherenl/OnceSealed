"""Copy the compiled RetirementRegistry ABI and bytecode from Foundry's out/ into core/chain/artifacts/.

The Python app and deploy script use this committed artifact, so they work without Foundry.
Run after changing the contract:

    cd contracts && forge build && cd .. && python scripts/export_artifact.py
"""

import json

from core.config import PROJECT_ROOT

SRC = PROJECT_ROOT / "contracts" / "out" / "RetirementRegistry.sol" / "RetirementRegistry.json"
DST = PROJECT_ROOT / "core" / "chain" / "artifacts" / "RetirementRegistry.json"


def main() -> None:
    out = json.loads(SRC.read_text(encoding="utf-8"))
    meta = out.get("metadata", {})
    artifact = {
        "contractName": "RetirementRegistry",
        "compiler": meta.get("compiler", {}).get("version"),
        "settings": {k: meta.get("settings", {}).get(k) for k in ("optimizer", "evmVersion")},
        "abi": out["abi"],
        "bytecode": out["bytecode"]["object"],
    }
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {DST.relative_to(PROJECT_ROOT)} (solc {artifact['compiler']}, {len(artifact['bytecode']) // 2} bytes)")


if __name__ == "__main__":
    main()
