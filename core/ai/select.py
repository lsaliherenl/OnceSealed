"""Pick the paragraphs most relevant to one principle, within a character budget."""

from core.ai.pdf_extract import Document, Paragraph
from core.ai.principles import Principle
from core.ai.quotes import normalize

DEFAULT_BUDGET_CHARS = 30_000
OVERVIEW_CHARS = 3_000  # opening paragraphs, so the model always knows the activity type
MIN_PARAGRAPH_CHARS = 40


def score_paragraph(text: str, keywords: tuple[str, ...]) -> int:
    t = normalize(text)
    return sum(t.count(k) for k in keywords)


def select_paragraphs(doc: Document, principle: Principle, budget_chars: int = DEFAULT_BUDGET_CHARS) -> list[Paragraph]:
    """Highest-scoring paragraphs plus their neighbours, returned in document order."""
    paras = doc.paragraphs
    scored = [
        (score_paragraph(p.text, principle.keywords), i)
        for i, p in enumerate(paras)
        if len(p.text) >= MIN_PARAGRAPH_CHARS
    ]
    scored = [(s, i) for s, i in scored if s > 0]
    scored.sort(key=lambda x: (-x[0], x[1]))

    chosen: set[int] = set()
    used = 0
    for i, p in enumerate(paras):
        if used >= OVERVIEW_CHARS:
            break
        if len(p.text) >= MIN_PARAGRAPH_CHARS:
            chosen.add(i)
            used += len(p.text)

    for _, i in scored:
        for j in (i - 1, i, i + 1):
            if j in chosen or not 0 <= j < len(paras):
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
