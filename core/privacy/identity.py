"""Identifiers as bytes32, matching the contract (keccak256 of a canonical string).

Buyers are identified by an LEI (ISO 17442 Legal Entity Identifier). The demo uses
fictional companies only: their LEIs have a valid ISO 7064 MOD 97-10 check, are
generated at random, and are not registered with GLEIF.
"""

import random
import re
import secrets
import string

from eth_utils import keccak

LEI_RE = re.compile(r"^[0-9A-Z]{18}[0-9]{2}$")
_ALPHABET = string.digits + string.ascii_uppercase


def text_id(text: str) -> bytes:
    """keccak256 of the UTF-8 text; the contract-side equivalent is keccak256(bytes(text))."""
    return keccak(text=text)


def project_id(offsetsdb_project_id: str) -> bytes:
    """`VCS1477` style id, exactly as OffsetsDB writes it (no dash)."""
    if not re.fullmatch(r"[A-Z]{2,4}\d+", offsetsdb_project_id):
        raise ValueError(f"unexpected project id format: {offsetsdb_project_id!r}")
    return text_id(offsetsdb_project_id)


def _mod97(chars: str) -> int:
    return int("".join(str(int(c, 36)) for c in chars)) % 97


def lei_check_digits(base18: str) -> str:
    """ISO 7064 MOD 97-10 check digits for the first 18 LEI characters."""
    if not re.fullmatch(r"[0-9A-Z]{18}", base18):
        raise ValueError("LEI base must be 18 characters [0-9A-Z]")
    return f"{98 - _mod97(base18 + '00'):02d}"


def is_valid_lei(lei: str) -> bool:
    return bool(LEI_RE.match(lei)) and _mod97(lei) == 1


def fictional_lei(rng: random.Random | None = None) -> str:
    """Random LEI-formatted code with valid check digits (characters 5-6 are '00' as in real LEIs)."""
    rng = rng or secrets.SystemRandom()
    base = "".join(rng.choice(_ALPHABET) for _ in range(4)) + "00" + "".join(rng.choice(_ALPHABET) for _ in range(12))
    return base + lei_check_digits(base)


def buyer_id(lei: str) -> bytes:
    lei = lei.strip().upper()
    if not is_valid_lei(lei):
        raise ValueError(f"invalid LEI: {lei!r}")
    return text_id("LEI:" + lei)
