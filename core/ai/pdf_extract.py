"""Extract text from a PDF as paragraphs with stable ids (``p<page>-<nn>``)."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class Paragraph:
    id: str
    page: int
    text: str


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


def extract(path: str | Path, min_chars: int = 3, id_prefix: str = "") -> Document:
    """Split every page into text blocks; each block becomes one paragraph."""
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
    return Document(path=str(path), sha256=file_sha256(path), page_count=page_count, paragraphs=paragraphs)


def extract_many(main: str | Path, extra: list[str | Path]) -> Document:
    """Treat a project document plus the documents it relies on (e.g. a CDM PDD referenced by a VCS
    project description) as one document. Paragraph ids of extra file k get the prefix ``x<k>-``."""
    docs = [extract(main)] + [extract(p, id_prefix=f"x{k}-") for k, p in enumerate(extra, start=1)]
    if len(docs) == 1:
        return docs[0]
    combined = hashlib.sha256("".join(d.sha256 for d in docs).encode()).hexdigest()
    return Document(path=" + ".join(d.path for d in docs), sha256=combined,
                    page_count=sum(d.page_count for d in docs),
                    paragraphs=[p for d in docs for p in d.paragraphs])
