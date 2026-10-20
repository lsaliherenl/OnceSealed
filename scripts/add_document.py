"""Register a downloaded project document in samples/manifest.json.

Copies the PDF into samples/pdfs/ under a canonical name, records its SHA-256 and source URL, and prints the
project's document coverage. The PDF itself stays out of git (samples/pdfs/ is ignored).

    python scripts/add_document.py VCS1477 monitoring_report "C:/Users/me/Downloads/MR 2015-2016.pdf" \\
        --url "https://registry.verra.org/..." --period 2015-01-01/2016-12-31
"""

import argparse
import sys
from pathlib import Path

from core.ai.pdf_extract import profile
from core.ai.sources import ROLES, get_project, register_document
from core.config import PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("role", choices=[r for r in ROLES if r != "project_description"])
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--url", help="registry URL the file was downloaded from")
    parser.add_argument("--doc-type", help="title as shown on the registry page (default: the role's name)")
    parser.add_argument("--period", help="monitoring/verification period, YYYY-MM-DD/YYYY-MM-DD")
    parser.add_argument("--covers", nargs="*", help="further roles the file serves (e.g. verification_report)")
    args = parser.parse_args()

    if not args.pdf.is_file():
        sys.exit(f"{args.pdf} not found")
    try:
        record = register_document(args.project_id, args.role, args.pdf, url=args.url, period=args.period,
                                   doc_type=args.doc_type, covers=args.covers)
    except ValueError as e:
        sys.exit(str(e))

    prof = profile(PROJECT_ROOT / record["local_path"])
    print(f"added {record['local_path']}: {prof.pages} pages, {prof.tables} tables, "
          f"{len(prof.pages_without_text)} pages without a text layer")
    if prof.pages_without_text:
        print("  warning: scanned pages need OCR before they can be read:", prof.pages_without_text[:20])
    cov = get_project(args.project_id).coverage()
    print(f"{args.project_id} holds {cov['held']}; still missing: {cov['missing'] or 'nothing'}")


if __name__ == "__main__":
    main()
