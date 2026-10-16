"""Which documents exist for each project, which of them we hold, and which ones the assessment read.

samples/manifest.json lists one entry per project: the main project document at the top level and further
files under ``extra_files``, each with a ``role``. PDFs are downloaded by hand into samples/pdfs/ and are not
committed; the manifest records their source URL and SHA-256 so a reader can fetch the same files.

A finished assessment would read the whole evidence trail: the project description, the validation report
and every monitoring and verification report. ``coverage`` says which of those are missing, so a report can
state what it did not read instead of implying that "no evidence found" means the evidence does not exist.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.ai.pdf_extract import file_sha256
from core.config import PROJECT_ROOT

MANIFEST = PROJECT_ROOT / "samples" / "manifest.json"

ROLES = {
    "project_description": "Project description (PD)",
    "validation_report": "Validation report (VVB)",
    "monitoring_report": "Monitoring report",
    "verification_report": "Verification report (VVB)",
    "supporting": "Supporting document",
}
# The documents that carry a project's evidence trail on a Verra project page.
EXPECTED_ROLES = ("project_description", "validation_report", "monitoring_report", "verification_report")


@dataclass(frozen=True)
class SourceFile:
    project_id: str
    role: str
    doc_type: str
    file_name: str
    local_path: str
    sha256: str | None
    url: str | None = None
    period: str | None = None  # monitoring/verification period, "YYYY-MM-DD/YYYY-MM-DD"
    covers: tuple[str, ...] = ()  # further roles a combined file serves, e.g. a joint PD and monitoring report

    @property
    def path(self) -> Path:
        return PROJECT_ROOT / self.local_path

    def status(self) -> str:
        """present | missing | hash_mismatch | unhashed"""
        if not self.path.exists():
            return "missing"
        if not self.sha256:
            return "unhashed"
        return "present" if file_sha256(self.path) == self.sha256 else "hash_mismatch"


@dataclass(frozen=True)
class ProjectSources:
    project_id: str
    name: str
    registry_url: str
    methodology: str
    methodology_version: str | None
    reversal_risk: bool | None
    files: list[SourceFile]

    def by_role(self, role: str) -> list[SourceFile]:
        return [f for f in self.files if f.role == role or role in f.covers]

    def coverage(self) -> dict[str, Any]:
        held = {r: len(self.by_role(r)) for r in ROLES if self.by_role(r)}
        return {"held": held, "missing": [r for r in EXPECTED_ROLES if r not in held]}


def _file(pid: str, d: dict[str, Any], role: str) -> SourceFile:
    return SourceFile(project_id=pid, role=d.get("role", role), doc_type=d["doc_type"], file_name=d["file_name"],
                      local_path=d["local_path"], sha256=d.get("sha256"), url=d.get("url"), period=d.get("period"),
                      covers=tuple(d.get("covers") or ()))


def load_manifest(path: Path = MANIFEST) -> list[ProjectSources]:
    out = []
    for d in json.loads(path.read_text(encoding="utf-8"))["documents"]:
        pid = d["project_id"]
        files = [_file(pid, d, "project_description")] + [_file(pid, x, "supporting") for x in d.get("extra_files") or []]
        out.append(ProjectSources(project_id=pid, name=d["project_name"], registry_url=d["registry_url"],
                                  methodology=d["methodology"], methodology_version=d.get("methodology_version"),
                                  reversal_risk=d.get("reversal_risk"), files=files))
    return out


def get_project(project_id: str, path: Path = MANIFEST) -> ProjectSources:
    for p in load_manifest(path):
        if p.project_id == project_id:
            return p
    raise KeyError(f"{project_id} is not in {path.name}")
