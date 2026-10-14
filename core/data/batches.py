"""Issuance batches with simulated serial ranges.

Real registries number credits within issuance batches; OffsetsDB has no serial
numbers, so we simulate ranges sized from real issuance quantities. The canonical
batch key is defined here and nowhere else, because batchId = keccak256(key).
Serial labels carry a "SIM" prefix so nobody mistakes them for real Verra serials.
"""

from dataclasses import dataclass

from core.privacy.identity import project_id as project_id_bytes
from core.privacy.identity import text_id


@dataclass(frozen=True)
class IssuanceBatch:
    project_id: str  # OffsetsDB format, e.g. "VCS1477"
    vintage: int
    batch_no: int
    first_serial: int
    last_serial: int

    def __post_init__(self):
        if not 0 < self.first_serial <= self.last_serial < 2**64:
            raise ValueError(f"invalid serial range {self.first_serial}-{self.last_serial}")

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

    def serial_label(self, start: int, end: int) -> str:
        """Human-readable label for a range in this batch (simulated, not a real Verra serial)."""
        return f"SIM-{self.project_id}-{self.vintage}-{self.batch_no:03d}-{start:09d}-{end:09d}"
