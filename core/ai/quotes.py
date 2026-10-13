"""Verify that a model-provided quote really appears in the source document.

Extracted PDF text differs from what a model copies: ligatures, line-break
hyphenation, curly quotes, dashes and whitespace. We normalize both sides
before searching. The strict search runs first; a looser letters-and-digits
search is used only for long quotes so short phrases cannot match by chance.
"""

import bisect
import re
import unicodedata
from dataclasses import dataclass

from core.ai.pdf_extract import Document

MIN_QUOTE_CHARS = 20
MIN_ALNUM_FALLBACK_CHARS = 40

_QUOTE_MAP = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    " ": " ",
})


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)  # also expands ligatures such as U+FB01 -> "fi"
    text = text.translate(_QUOTE_MAP)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)  # join words hyphenated across lines
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def alnum(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", normalize(text))


@dataclass(frozen=True)
class QuoteCheck:
    verified: bool
    method: str  # exact | exact_relocated | alnum | alnum_relocated | rejected:<reason>
    paragraph_id: str | None
    page: int | None


class QuoteVerifier:
    def __init__(self, doc: Document):
        self._paras = doc.paragraphs
        self._index = {p.id: i for i, p in enumerate(self._paras)}
        self._norm = [normalize(p.text) for p in self._paras]
        self._alnum = [re.sub(r"[^0-9a-z]", "", n) for n in self._norm]
        self._norm_doc, self._norm_starts = self._join(self._norm, " ")
        self._alnum_doc, self._alnum_starts = self._join(self._alnum, "")

    @staticmethod
    def _join(parts: list[str], sep: str) -> tuple[str, list[int]]:
        starts, pos = [], 0
        for part in parts:
            starts.append(pos)
            pos += len(part) + len(sep)
        return sep.join(parts), starts

    def _window(self, i: int, texts: list[str], sep: str) -> str:
        # The cited paragraph plus its neighbours: PDF blocks often split one sentence in two.
        return sep.join(texts[max(0, i - 1): i + 2])

    def _locate(self, starts: list[int], offset: int) -> int:
        return bisect.bisect_right(starts, offset) - 1

    def _result(self, method: str, i: int) -> QuoteCheck:
        p = self._paras[i]
        return QuoteCheck(True, method, p.id, p.page)

    def check(self, quote: str, paragraph_id: str | None) -> QuoteCheck:
        if "..." in quote or "…" in quote:
            return QuoteCheck(False, "rejected:ellipsis", paragraph_id, None)
        q = normalize(quote)
        if len(q) < MIN_QUOTE_CHARS:
            return QuoteCheck(False, "rejected:too_short", paragraph_id, None)

        i = self._index.get(paragraph_id or "")
        if i is not None and q in self._window(i, self._norm, " "):
            return self._result("exact", i)
        pos = self._norm_doc.find(q)
        if pos >= 0:
            return self._result("exact_relocated", self._locate(self._norm_starts, pos))

        qa = re.sub(r"[^0-9a-z]", "", q)
        if len(qa) >= MIN_ALNUM_FALLBACK_CHARS:
            if i is not None and qa in self._window(i, self._alnum, ""):
                return self._result("alnum", i)
            pos = self._alnum_doc.find(qa)
            if pos >= 0:
                return self._result("alnum_relocated", self._locate(self._alnum_starts, pos))

        return QuoteCheck(False, "rejected:not_found", paragraph_id, None)
