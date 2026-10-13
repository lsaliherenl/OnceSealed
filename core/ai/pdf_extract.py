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


def extract(path: str | Path, min_chars: int = 3) -> Document:
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
                paragraphs.append(Paragraph(id=f"p{page}-{n:02d}", page=page, text=text))
    return Document(path=str(path), sha256=file_sha256(path), page_count=page_count, paragraphs=paragraphs)
