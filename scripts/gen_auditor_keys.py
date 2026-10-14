"""Create the auditor's vault keypair (libsodium) and store it in .env if not already set.

Prints only the public key. In a real deployment the private key would live with the
auditor alone; in this demo one machine plays every role, so both go into .env.

    python scripts/gen_auditor_keys.py
"""

import re

from core.config import PROJECT_ROOT
from core.privacy.vault import generate_keypair


def main() -> None:
    env = PROJECT_ROOT / ".env"
    text = env.read_text(encoding="utf-8")
    if re.search(r"^AUDITOR_BOX_PRIVATE_KEY=\S+", text, re.M):
        print("AUDITOR_BOX_PRIVATE_KEY already set; not overwriting.")
        return
    public, private = generate_keypair()
    text = re.sub(r"^AUDITOR_BOX_PUBLIC_KEY=.*$", f"AUDITOR_BOX_PUBLIC_KEY={public}", text, flags=re.M)
    text = re.sub(r"^AUDITOR_BOX_PRIVATE_KEY=.*$", f"AUDITOR_BOX_PRIVATE_KEY={private}", text, flags=re.M)
    env.write_text(text, encoding="utf-8")
    print(f"auditor vault public key: {public}")


if __name__ == "__main__":
    main()
