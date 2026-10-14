"""Settings loaded from the project's .env file."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class AISettings:
    base_url: str
    model: str
    api_key: str


ROLES = ("deployer", "assessor", "operator", "auditor")
ANVIL_RPC_URL = "http://127.0.0.1:8545"


@dataclass(frozen=True)
class ChainSettings:
    network: str  # "anvil" | "sepolia"
    rpc_url: str
    private_keys: dict[str, str]  # role -> hex private key (test wallets only)


def chain_settings(network: str = "anvil", rpc_url: str | None = None) -> ChainSettings:
    if network == "anvil":
        url = rpc_url or os.environ.get("ANVIL_RPC_URL", ANVIL_RPC_URL)
    elif network == "sepolia":
        url = rpc_url or os.environ.get("SEPOLIA_RPC_URL", "")
    else:
        raise ValueError(f"unknown network {network!r}")
    if not url:
        raise RuntimeError(f"no RPC URL for {network}")
    keys = {}
    for role in ROLES:
        key = os.environ.get(f"{role.upper()}_PRIVATE_KEY", "")
        if not key:
            raise RuntimeError(f"{role.upper()}_PRIVATE_KEY is not set in .env")
        keys[role] = key
    return ChainSettings(network=network, rpc_url=url, private_keys=keys)


def auditor_box_keys() -> tuple[str, str | None]:
    """(public, private) base64 keys of the auditor vault; private is None if not on this machine."""
    public = os.environ.get("AUDITOR_BOX_PUBLIC_KEY", "")
    if not public:
        raise RuntimeError("AUDITOR_BOX_PUBLIC_KEY is not set; run scripts/gen_auditor_keys.py")
    return public, os.environ.get("AUDITOR_BOX_PRIVATE_KEY") or None


def ai_settings() -> AISettings:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in .env")
    return AISettings(
        base_url=os.environ.get("AI_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.environ.get("AI_MODEL", "typesafe/jev-router"),
        api_key=api_key,
    )
