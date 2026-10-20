"""Create the demo role tokens for the API (operator, auditor, assessor) in .env if missing.

The tokens are not printed; the web app reads them from its own environment (see web/README).

    python scripts/gen_api_tokens.py
"""

import re
import secrets

from core.config import PROJECT_ROOT

KEYS = ["OPERATOR_API_TOKEN", "AUDITOR_API_TOKEN", "ASSESSOR_API_TOKEN"]


def main() -> None:
    env = PROJECT_ROOT / ".env"
    text = env.read_text(encoding="utf-8")
    added = []
    for key in KEYS:
        if re.search(rf"^{key}=\S+", text, re.M):
            continue
        value = secrets.token_urlsafe(24)
        if re.search(rf"^{key}=", text, re.M):
            text = re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.M)
        else:
            text = text.rstrip("\n") + f"\n{key}={value}\n"
        added.append(key)
    env.write_text(text, encoding="utf-8")
    print(f"set in .env: {added or 'nothing (already set)'}")


if __name__ == "__main__":
    main()
