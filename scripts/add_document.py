"""Register a downloaded project document in samples/manifest.json.

Copies the PDF into samples/pdfs/ under a canonical name, records its SHA-256 and source URL, and prints the
project's document coverage. The PDF itself stays out of git (samples/pdfs/ is ignored).

    python scripts/add_document.py VCS1477 monitoring_report "C:/Users/me/Downloads/MR 2015-2016.pdf" \\
        --url "https://registry.verra.org/..." --period 2015-01-01/2016-12-31
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from core.ai.pdf_extract import file_sha256, profile
from core.ai.sources import MANIFEST, ROLES, get_project
from core.config import PROJECT_ROOT

SHORT = {"project_description": "PD", "validation_report": "VAL", "monitoring_report": "MR",
         "verification_report": "VER", "supporting": "DOC"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("role", choices=[r for r in ROLES if r != "project_description"])
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--url", help="registry URL the file was downloaded from")
    parser.add_argument("--doc-type", help="title as shown on the registry page (default: the role's name)")
    parser.add_argument("--period", help="monitoring/verification period, YYYY-MM-DD/YYYY-MM-DD")
    args = parser.parse_args()

    if not args.pdf.is_file():
        sys.exit(f"{args.pdf} not found")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entry = next((d for d in manifest["documents"] if d["project_id"] == args.project_id), None)
    if entry is None:
        sys.exit(f"{args.project_id} is not in samples/manifest.json")

    sha = file_sha256(args.pdf)
    extra = entry.setdefault("extra_files", [])
    if any(x.get("sha256") == sha for x in extra) or entry.get("sha256") == sha:
        sys.exit("this file is already registered")

    n = 1 + sum(1 for x in extra if x.get("role") == args.role)
    dest = PROJECT_ROOT / "samples" / "pdfs" / f"{args.project_id}_{SHORT[args.role]}{n}.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.pdf, dest)

    record = {"role": args.role, "doc_type": args.doc_type or ROLES[args.role], "file_name": args.pdf.name,
              "local_path": dest.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha}
    if args.url:
        record["url"] = args.url
    if args.period:
        record["period"] = args.period
    extra.append(record)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    prof = profile(dest)
    print(f"added {record['local_path']}: {prof.pages} pages, {prof.tables} tables, "
          f"{len(prof.pages_without_text)} pages without a text layer")
    if prof.pages_without_text:
        print("  warning: scanned pages need OCR before they can be read:", prof.pages_without_text[:20])
    cov = get_project(args.project_id).coverage()
    print(f"{args.project_id} holds {cov['held']}; still missing: {cov['missing'] or 'nothing'}")


if __name__ == "__main__":
    main()
