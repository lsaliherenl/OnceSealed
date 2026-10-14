"""Local Anvil chain helpers for the demo script and the end-to-end tests."""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

from web3 import Web3


def anvil_binary() -> str | None:
    found = shutil.which("anvil")
    if found:
        return found
    for name in ("anvil.exe", "anvil"):
        p = Path.home() / ".foundry" / "bin" / name
        if p.exists():
            return str(p)
    return None


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_anvil(port: int, extra_args: list[str] | None = None) -> subprocess.Popen:
    binary = anvil_binary()
    if binary is None:
        raise FileNotFoundError("anvil not found; install Foundry (https://getfoundry.sh)")
    proc = subprocess.Popen([binary, "--port", str(port), "--silent", *(extra_args or [])],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    w3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{port}"))
    for _ in range(100):
        if w3.is_connected():
            return proc
        time.sleep(0.1)
    proc.kill()
    raise TimeoutError("anvil did not start")


def fund(w3: Web3, addresses: list[str], wei: int = 10**20) -> None:
    """Anvil-only: give test accounts a balance without a faucet."""
    for a in addresses:
        w3.provider.make_request("anvil_setBalance", [a, hex(wei)])
