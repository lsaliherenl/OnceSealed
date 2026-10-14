"""Pick the paragraphs most relevant to one principle, within a character budget."""

from collections import Counter

from core.ai.pdf_extract import Document, Paragraph
from core.ai.principles import Principle
from core.ai.quotes import normalize

DEFAULT_BUDGET_CHARS = 30_000
OVERVIEW_CHARS = 3_000  # opening paragraphs, so the model always knows the activity type
MIN_PARAGRAPH_CHARS = 40
BOILERPLATE_MIN_REPEATS = 3  # short text repeated on this many pages is a page header/footer


def score_paragraph(text: str, keywords: tuple[str, ...]) -> int:
    t = normalize(text)
    return sum(t.count(k) for k in keywords)


def _content_chars(text: str) -> int:
    return len(" ".join(text.split()))  # PDF blocks often pad headers with long runs of spaces


def _usable(doc: Document) -> list[bool]:
    """False for fragments (page numbers, short labels) and for headers/footers repeated across pages."""
    keys = [normalize(p.text) for p in doc.paragraphs]
    repeats = Counter(k for k in keys if len(k) < 200)
    return [_content_chars(p.text) >= MIN_PARAGRAPH_CHARS and repeats.get(k, 0) < BOILERPLATE_MIN_REPEATS
            for p, k in zip(doc.paragraphs, keys)]


def select_paragraphs(doc: Document, principle: Principle, budget_chars: int = DEFAULT_BUDGET_CHARS,
                      overview_chars: int = OVERVIEW_CHARS, neighbours: bool = True) -> list[Paragraph]:
    """Highest-scoring paragraphs plus their neighbours, returned in document order."""
    paras = doc.paragraphs
    usable = _usable(doc)
    scored = [(score_paragraph(p.text, principle.keywords), i) for i, p in enumerate(paras) if usable[i]]
    scored = [(s, i) for s, i in scored if s > 0]
    scored.sort(key=lambda x: (-x[0], x[1]))

    chosen: set[int] = set()
    used = 0
    for i, p in enumerate(paras):
        if used >= overview_chars:
            break
        if usable[i]:
            chosen.add(i)
            used += len(p.text)

    for _, i in scored:
        for j in ((i - 1, i, i + 1) if neighbours else (i,)):
            if j in chosen or not 0 <= j < len(paras) or not usable[j]:
                continue
            size = len(paras[j].text)
            if used + size > budget_chars:
                continue
            chosen.add(j)
            used += size
        if used >= budget_chars:
            break
    return [paras[i] for i in sorted(chosen)]


def render_excerpts(paragraphs: list[Paragraph]) -> str:
    return "\n\n".join(f"[{p.id}] {p.text}" for p in paragraphs)
