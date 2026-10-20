"""Take the 3:2 screenshots for the Devpost gallery (docs/gallery/) from a running demo.

    python scripts/demo_up.py          # in another terminal (Sepolia, so the role screens have data)
    python scripts/gallery.py
    python scripts/gallery.py --dark     # dark theme instead of light
    python scripts/gallery.py --base https://once-sealed.vercel.app --out somewhere   # check the hosted site

Drives a local headless Chrome or Edge over the DevTools protocol: each page gets time to read the chain, then is
scrolled to the section shown before the capture.
"""

import asyncio
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "gallery"
BASE = "http://localhost:3000"
WIDTH, HEIGHT = 1500, 1000  # Devpost recommends 3:2
PORT = 9333
THEME = "dark" if "--dark" in sys.argv else "light"
# (file name, path, element id to scroll to or None, seconds to wait for chain reads)
SHOTS = [
    ("01-overview", "/", None, 6),
    ("02-project-quality", "/projects", None, 6),
    ("03-report-provenance", "/projects/VCS985", None, 12),
    ("04-report-checks", "/projects/VCS985", "ccp-h", 8),
    ("05-data-checks", "/projects/VCS985", "checks-h", 8),
    ("06-report-versions", "/projects/VCS138", "versions-h", 15),
    ("07-verify", "/verify?q=3", None, 12),
    ("08-auditor", "/auditor", None, 12),
    ("09-assess", "/assess", None, 8),
    ("10-review", "/review", None, 8),
]
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "google-chrome", "chromium"]


def browser() -> str:
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    sys.exit("no Chrome or Edge found")


async def capture(ws_url: str) -> None:
    async with websockets.connect(ws_url, max_size=50_000_000) as ws:
        n = 0

        async def call(method: str, **params):
            nonlocal n
            n += 1
            await ws.send(json.dumps({"id": n, "method": method, "params": params}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == n:
                    return msg.get("result", {})

        await call("Emulation.setDeviceMetricsOverride", width=WIDTH, height=HEIGHT, deviceScaleFactor=1, mobile=False)
        # light theme: the site follows the system setting (next-themes), and Devpost's page is white
        await call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": THEME}])
        await call("Page.addScriptToEvaluateOnNewDocument",
                   source=f"try {{ localStorage.setItem('theme', '{THEME}') }} catch (e) {{}}")
        await call("Page.enable")
        for name, path, anchor, wait in SHOTS:
            await call("Page.navigate", url=BASE + path)
            await asyncio.sleep(wait)
            if anchor:
                await call("Runtime.evaluate", expression=(
                    f"document.getElementById('{anchor}')?.scrollIntoView({{block: 'start'}}); window.scrollBy(0, -24)"))
                await asyncio.sleep(2)
            shot = await call("Page.captureScreenshot", format="png")
            (OUT / f"{name}.png").write_bytes(base64.b64decode(shot["data"]))
            print(f"wrote {OUT / name}.png")


def main() -> None:
    global BASE, OUT
    if "--base" in sys.argv:
        BASE = sys.argv[sys.argv.index("--base") + 1].rstrip("/")
    if "--out" in sys.argv:
        OUT = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        proc = subprocess.Popen([browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                                 f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                                 f"--window-size={WIDTH},{HEIGHT}", "about:blank"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                    break
                except OSError:
                    time.sleep(0.2)
            else:
                sys.exit("the browser did not start")
            page = next(p for p in pages if p.get("type") == "page")
            asyncio.run(capture(page["webSocketDebuggerUrl"]))
        finally:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    main()
