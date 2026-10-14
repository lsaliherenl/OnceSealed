"""Fictional buyer companies for the demo (data/demo_buyers.json).

Names are invented and LEIs are random with valid check digits; none is registered with GLEIF.
Deterministic, so the demo shows the same companies every time.

    python scripts/gen_demo_buyers.py
"""

import json
import random

from core.config import PROJECT_ROOT
from core.privacy.identity import fictional_lei

# Deliberately invented names; the UI also labels them fictional.
NAMES = [
    "Quillmere Freight",
    "Vantorra Cement",
    "Aerolune Airways",
    "Glimmerstack Data",
    "Orchardine Retail",
    "Ferrowick Steel",
]


def main() -> None:
    rng = random.Random(20261015)
    buyers = [{"name": n, "lei": fictional_lei(rng), "fictional": True} for n in NAMES]
    out = {"note": "Fictional companies for the OnceSealed demo. LEIs have valid check digits but are not registered.",
           "buyers": buyers}
    path = PROJECT_ROOT / "data" / "demo_buyers.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(PROJECT_ROOT)}: {[b['name'] for b in buyers]}")


if __name__ == "__main__":
    main()
