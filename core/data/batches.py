"""Issuance batches with simulated serial ranges.

Real registries number credits within issuance batches; OffsetsDB has no serial
numbers, so we simulate ranges sized from real issuance quantities. The canonical
batch key is defined here and nowhere else, because batchId = keccak256(key).
Serial labels carry a "SIM" prefix so nobody mistakes them for real Verra serials.

Demo batches use standard lots (DEFAULT_LOT_SIZE): every private retirement is exactly one
lot, so the retired amount cannot single out a buyer (threat T12 in docs/threat_model.md).
"""

import json
from dataclasses import dataclass

from core.config import PROJECT_ROOT
from core.privacy.identity import project_id as project_id_bytes
from core.privacy.identity import text_id


DEFAULT_LOT_SIZE = 1_000  # tonnes; see data/derived/linkability.json for the trade-off


@dataclass(frozen=True)
class IssuanceBatch:
    project_id: str  # OffsetsDB format, e.g. "VCS1477"
    vintage: int
    batch_no: int
    first_serial: int
    last_serial: int
    lot_size: int = 0  # 0 = free ranges

    def __post_init__(self):
        if not 0 < self.first_serial <= self.last_serial < 2**64:
            raise ValueError(f"invalid serial range {self.first_serial}-{self.last_serial}")
        if self.lot_size < 0:
            raise ValueError("lot size must be >= 0")

    @property
    def key(self) -> str:
        return f"{self.project_id}|{self.vintage}|{self.batch_no:03d}"

    @property
    def batch_id(self) -> bytes:
        return text_id(self.key)

    @property
    def project_id_bytes(self) -> bytes:
        return project_id_bytes(self.project_id)

    @property
    def quantity(self) -> int:
        return self.last_serial - self.first_serial + 1

    def lot_ranges(self, start: int, end: int) -> list[tuple[int, int]]:
        """Split [start, end] into the batch's lots (the same rule the contract enforces).

        Free-range batches return the range unchanged. Raises ValueError if the range does not
        start on a lot boundary or ends inside a lot (other than at the end of the batch)."""
        if not self.first_serial <= start <= end <= self.last_serial:
            raise ValueError(f"range {start}-{end} is outside the batch {self.first_serial}-{self.last_serial}")
        if self.lot_size == 0:
            return [(start, end)]
        lot = self.lot_size
        if (start - self.first_serial) % lot != 0:
            raise ValueError(f"start {start} is not on a {lot:,}-unit lot boundary")
        if (end - start + 1) % lot != 0 and end != self.last_serial:
            raise ValueError(f"the range must cover whole lots of {lot:,} units (or end at the batch end)")
        return [(s, min(s + lot - 1, end)) for s in range(start, end + 1, lot)]

    def serial_label(self, start: int, end: int) -> str:
        """Human-readable label for a range in this batch (simulated, not a real Verra serial)."""
        return f"SIM-{self.project_id}-{self.vintage}-{self.batch_no:03d}-{start:09d}-{end:09d}"


BATCHES_PATH = PROJECT_ROOT / "data" / "batches.json"


def load_batches(project_id: str | None = None) -> list[IssuanceBatch]:
    """Demo batches built by scripts/build_batches.py from real OffsetsDB issuance records."""
    data = json.loads(BATCHES_PATH.read_text(encoding="utf-8"))
    out = [IssuanceBatch(b["project_id"], b["vintage"], b["batch_no"], b["first_serial"], b["last_serial"],
                         b.get("lot_size", 0)) for b in data["batches"]]
    return [b for b in out if project_id is None or b.project_id == project_id]
