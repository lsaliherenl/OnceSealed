"""Extract text from a PDF as paragraphs with stable ids (``p<page>-<nn>``), and its tables (``p<page>-t<n>``).

Tables are detected by PyMuPDF's ``find_tables``. Text blocks already contain the cell text, but in reading
order rather than row by row, which scrambles the numeric tables (emission estimates, IRR calculations)
that carry much of a project document's evidence.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class Paragraph:
    id: str
    page: int
    text: str
    kind: str = "text"  # text | table


@dataclass(frozen=True)
class Table:
    id: str
    page: int
    rows: list[list[str]]  # cell text with whitespace collapsed; "" for empty cells

    def render(self) -> str:
        """One line per row, non-empty cells joined by " | "."""
        return "\n".join(" | ".join(c for c in row if c) for row in self.rows if any(row))


@dataclass(frozen=True)
class Document:
    path: str
    sha256: str
    page_count: int
    paragraphs: list[Paragraph]

    def by_id(self) -> dict[str, Paragraph]:
        return {p.id: p for p in self.paragraphs}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _cell(value: object) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def extract_tables(path: str | Path, id_prefix: str = "") -> list[Table]:
    tables: list[Table] = []
    with pymupdf.open(path) as doc:
        for page_index in range(doc.page_count):
            found = doc[page_index].find_tables().tables
            for n, t in enumerate(found, start=1):
                rows = [[_cell(c) for c in row] for row in t.extract()]
                if any(any(row) for row in rows):
                    page = page_index + 1
                    tables.append(Table(id=f"{id_prefix}p{page}-t{n}", page=page, rows=rows))
    return tables


@dataclass(frozen=True)
class Profile:
    """What a reader could get out of a file: pages, pages without a text layer (scans need OCR), tables."""

    sha256: str
    pages: int
    pages_without_text: list[int]
    text_chars: int
    tables: int


def profile(path: str | Path) -> Profile:
    path = Path(path)
    with pymupdf.open(path) as doc:
        texts = [doc[i].get_text() for i in range(doc.page_count)]
        pages = doc.page_count
    return Profile(sha256=file_sha256(path), pages=pages,
                   pages_without_text=[i + 1 for i, t in enumerate(texts) if len(t.strip()) < 20],
                   text_chars=sum(len(t) for t in texts), tables=len(extract_tables(path)))


def extract(path: str | Path, min_chars: int = 3, id_prefix: str = "", tables: bool = False) -> Document:
    """Split every page into text blocks; each block becomes one paragraph. With ``tables``, each detected
    table is added after the page's blocks as one more paragraph, rendered row by row."""
    path = Path(path)
    paragraphs: list[Paragraph] = []
    with pymupdf.open(path) as doc:
        page_count = doc.page_count
        for page_index in range(page_count):
            blocks = doc[page_index].get_text("blocks", sort=True)
            n = 0
            for block in blocks:
                text, block_type = block[4], block[6]
                if block_type != 0:  # 0 = text, 1 = image
                    continue
                text = text.strip()
                if len(text) < min_chars:
                    continue
                n += 1
                page = page_index + 1
                paragraphs.append(Paragraph(id=f"{id_prefix}p{page}-{n:02d}", page=page, text=text))
    if tables:
        by_page: dict[int, list[Paragraph]] = {}
        for t in extract_tables(path, id_prefix):
            by_page.setdefault(t.page, []).append(Paragraph(id=t.id, page=t.page, text=t.render(), kind="table"))
        merged: list[Paragraph] = []
        for i, p in enumerate(paragraphs):
            merged.append(p)
            if i + 1 == len(paragraphs) or paragraphs[i + 1].page != p.page:
                merged.extend(by_page.pop(p.page, []))
        paragraphs = merged + [p for ps in by_page.values() for p in ps]  # tables on pages without text blocks
    return Document(path=str(path), sha256=file_sha256(path), page_count=page_count, paragraphs=paragraphs)


def extract_many(main: str | Path, extra: list[str | Path], tables: bool = False) -> Document:
    """Treat a project document plus the documents it relies on (e.g. a CDM PDD referenced by a VCS
    project description) as one document. Paragraph ids of extra file k get the prefix ``x<k>-``."""
    docs = [extract(main, tables=tables)] + [extract(p, id_prefix=f"x{k}-", tables=tables)
                                             for k, p in enumerate(extra, start=1)]
    if len(docs) == 1:
        return docs[0]
    combined = hashlib.sha256("".join(d.sha256 for d in docs).encode()).hexdigest()
    return Document(path=" + ".join(d.path for d in docs), sha256=combined,
                    page_count=sum(d.page_count for d in docs),
                    paragraphs=[p for d in docs for p in d.paragraphs])
