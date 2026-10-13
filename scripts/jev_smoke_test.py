"""Smoke test of the AI quality pipeline on one PDF.

Usage:
    python scripts/jev_smoke_test.py samples/pdfs/VCS1477_PD.pdf --principles permanence
    python scripts/jev_smoke_test.py samples/pdfs/VCS1851_PD.pdf --dry-run

Results are written to data/runs/<pdf-stem>/<timestamp>-<principle>.json
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from core.ai.assess import PROMPT_VERSION, assess_principle
from core.ai.client import ChatClient
from core.ai.pdf_extract import extract
from core.ai.principles import BY_KEY, PRINCIPLES
from core.ai.quotes import QuoteVerifier
from core.ai.select import render_excerpts, select_paragraphs
from core.config import PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--principles", nargs="*", default=[p.key for p in PRINCIPLES], choices=list(BY_KEY))
    parser.add_argument("--dry-run", action="store_true", help="extract and select only; no API call")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252 (no "₂")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    t0 = time.time()
    doc = extract(args.pdf)
    print(f"{Path(args.pdf).name}: {doc.page_count} pages, {len(doc.paragraphs)} paragraphs, "
          f"sha256={doc.sha256[:16]}..., extracted in {time.time() - t0:.1f}s")

    if args.dry_run:
        for key in args.principles:
            paras = select_paragraphs(doc, BY_KEY[key])
            pages = sorted({p.page for p in paras})
            print(f"  {key:22s} {len(paras):3d} paragraphs, {len(render_excerpts(paras)):6d} chars, "
                  f"pages {pages[:12]}{'...' if len(pages) > 12 else ''}")
        return

    client = ChatClient()
    verifier = QuoteVerifier(doc)
    out_dir = PROJECT_ROOT / "data" / "runs" / Path(args.pdf).stem
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")

    for key in args.principles:
        t1 = time.time()
        result = assess_principle(doc, BY_KEY[key], client, verifier)
        record = {"pdf": args.pdf, "pdf_sha256": doc.sha256, "prompt_version": PROMPT_VERSION,
                  "requested_model": client.settings.model, "result": result.to_dict()}
        (out_dir / f"{stamp}-{key}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        cost = (result.usage or {}).get("cost")
        print(f"\n=== {key}  ({time.time() - t1:.0f}s, served by {result.served_model}, cost {cost})")
        print(f"status={result.status} score={result.score}  (model said {result.model_status}/{result.model_score})")
        print(f"quotes verified={len(result.quotes)} dropped={result.dropped_findings}")
        print(f"rationale: {result.rationale}")
        for q in result.quotes:
            print(f"  [ok {q.method} {q.paragraph_id} p.{q.page}] {q.text[:160]}")
        for d in result.dropped:
            print(f"  [DROPPED {d.reason} {d.paragraph_id}] {d.text[:160]}")
        if result.error:
            print(f"  error: {result.error}")


if __name__ == "__main__":
    main()
