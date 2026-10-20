"""Start the whole demo with one command: the OnceSealed API and the web app (and a local chain with --local).

    python scripts/demo_up.py            # Sepolia: needs .env with the test-wallet keys and SEPOLIA_RPC_URL
    python scripts/demo_up.py --local    # throwaway Anvil chain with temporary keys; no .env needed

Then open http://localhost:3000. Ctrl+C stops everything.

In --local mode the operator, auditor and assessor screens act on the local chain, while the public pages
(project reports, verify) keep reading Sepolia, so a retirement made locally is not shown on the verify page.
Requirements: Python packages from requirements.txt, Node.js 20.9+ (`cd web && npm ci` once), and Foundry's
anvil for --local.
"""

import argparse
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eth_account import Account  # noqa: E402

from core.chain import anvil  # noqa: E402
from core.config import ROLES  # noqa: E402
from core.privacy.vault import generate_keypair  # noqa: E402

API_PORT, WEB_PORT = 8000, 3000
TOKEN_KEYS = ("OPERATOR_API_TOKEN", "AUDITOR_API_TOKEN", "ASSESSOR_API_TOKEN")


def wait_for(url: str, seconds: int, proc: subprocess.Popen) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except OSError:
            time.sleep(1)
    return False


def build_is_current() -> bool:
    """True when web/.next was built after every change to the web sources and the exported data."""
    build_id = ROOT / "web" / ".next" / "BUILD_ID"
    if not build_id.exists():
        return False
    built = build_id.stat().st_mtime
    sources = [ROOT / "web" / d for d in ("src", "public")] + [ROOT / "web" / "next.config.ts"]
    newest = max((f.stat().st_mtime for d in sources for f in ([d] if d.is_file() else d.rglob("*")) if f.is_file()),
                 default=0)
    return newest <= built


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--local", action="store_true", help="throwaway Anvil chain with temporary keys")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    for port in (API_PORT, WEB_PORT):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                sys.exit(f"port {port} is already in use: stop the other server first")

    npm = shutil.which("npm")
    if npm is None:
        sys.exit("npm not found: install Node.js 20.9+")
    if not (ROOT / "web" / "node_modules").exists():
        sys.exit("web dependencies missing: run `cd web && npm ci` once")

    env = dict(os.environ)
    procs: list[subprocess.Popen] = []
    if args.local:
        port = anvil.free_port()
        procs.append(anvil.start_anvil(port))
        env.update({"ONCESEALED_NETWORK": "anvil", "ANVIL_RPC_URL": f"http://127.0.0.1:{port}"})
        for role in ROLES:  # temporary keys, funded by anvil when the API deploys the contract
            env[f"{role.upper()}_PRIVATE_KEY"] = "0x" + Account.create().key.hex().removeprefix("0x")
        env["AUDITOR_BOX_PUBLIC_KEY"], env["AUDITOR_BOX_PRIVATE_KEY"] = generate_keypair()
        for key in TOKEN_KEYS:
            env[key] = secrets.token_urlsafe(24)
    else:
        if not (ROOT / ".env").exists():
            sys.exit("no .env: copy .env.example and fill the Sepolia test keys, or run with --local")
        env["ONCESEALED_NETWORK"] = "sepolia"
        subprocess.run([sys.executable, "scripts/gen_api_tokens.py"], cwd=ROOT, check=True)  # adds missing tokens

    try:
        api = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.server:app", "--port", str(API_PORT)],
                               cwd=ROOT, env=env)
        procs.append(api)
        print(f"starting the API on http://127.0.0.1:{API_PORT} ...")
        if not wait_for(f"http://127.0.0.1:{API_PORT}/api/health", 120, api):
            sys.exit("the API did not start; see the messages above")

        if not build_is_current():
            print("building the web app (its sources changed since the last build) ...")
            subprocess.run([npm, "run", "build"], cwd=ROOT / "web", env=env, check=True)
        web_cmd = [npm, "run", "start", "--", "--port", str(WEB_PORT)]
        web = subprocess.Popen(web_cmd, cwd=ROOT / "web", env={**env, "ONCESEALED_API_URL": f"http://127.0.0.1:{API_PORT}"})
        procs.append(web)
        if not wait_for(f"http://127.0.0.1:{WEB_PORT}/", 180, web):
            sys.exit("the web app did not start; see the messages above")
        mode = "a throwaway local chain" if args.local else "Sepolia"
        print(f"\nOnceSealed is running on {mode}: http://localhost:{WEB_PORT}  (Ctrl+C to stop)")
        print("  /retire  operator · /auditor  auditor · /assess  assessor · /verify and /projects  public\n")
        while all(p.poll() is None for p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in reversed(procs):
            if p.poll() is None:
                if os.name == "nt":  # npm on Windows leaves its node child running after terminate()
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
                else:
                    p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
