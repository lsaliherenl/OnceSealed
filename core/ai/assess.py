"""Assess one ICVCM principle: select excerpts, ask the model, verify every quote."""

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import json_repair
from pydantic import BaseModel, ValidationError

from core.ai.client import ChatClient, Completion
from core.ai.pdf_extract import Document
from core.ai.principles import Principle
from core.ai.quotes import QuoteVerifier
from core.ai.select import render_excerpts, select_paragraphs

log = logging.getLogger(__name__)

PROMPT_VERSION = "v1"

Status = Literal["evidence_found", "evidence_weak", "no_evidence", "not_applicable"]

SCORE_BANDS: dict[str, tuple[int, int]] = {
    "evidence_found": (60, 100),
    "evidence_weak": (20, 59),
    "no_evidence": (0, 19),
    "not_applicable": (0, 0),
}

SYSTEM_PROMPT = """You assist carbon-credit quality auditors. You assess ONE ICVCM Core Carbon Principle using ONLY the numbered excerpts of a project document given by the user.

Rules:
1. Support every claim with quotes copied VERBATIM from the excerpts: one contiguous span of 1-2 sentences, 40-300 characters, copied character for character. No ellipses, no paraphrasing, no joining of separate passages.
2. Each quote carries the paragraph_id shown in square brackets before the excerpt it comes from (for example "p12-03").
3. Report evidence, not verdicts. Say what the document does or does not show; never call a project good, bad or fraudulent.
4. status:
   - evidence_found: the document gives specific, substantive evidence for the principle.
   - evidence_weak: evidence is generic, asserted without support, or incomplete.
   - no_evidence: the excerpts contain nothing relevant.
   - not_applicable: the principle does not apply to this activity type; quote the evidence of the activity type.
5. score 0-100 must match the status: evidence_found 60-100, evidence_weak 20-59, no_evidence 0-19, not_applicable 0.
6. Give 1-4 quotes (0 only for no_evidence). rationale: at most 80 words, English.
Respond with JSON only."""

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["principle", "status", "score", "rationale", "quotes"],
    "properties": {
        "principle": {"type": "string"},
        "status": {"type": "string", "enum": list(SCORE_BANDS)},
        "score": {"type": "integer"},
        "rationale": {"type": "string"},
        "quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["paragraph_id", "text"],
                "properties": {"paragraph_id": {"type": "string"}, "text": {"type": "string"}},
            },
        },
    },
}


class _Quote(BaseModel):
    paragraph_id: str
    text: str


class _Finding(BaseModel):
    principle: str
    status: Status
    score: int
    rationale: str
    quotes: list[_Quote]


@dataclass
class VerifiedQuote:
    text: str
    paragraph_id: str
    page: int
    method: str


@dataclass
class DroppedQuote:
    text: str
    paragraph_id: str
    reason: str


@dataclass
class PrincipleResult:
    principle: str
    status: str
    score: int | None  # None when not_applicable or assessment_failed; excluded from the overall score
    rationale: str
    quotes: list[VerifiedQuote]
    dropped_findings: int
    dropped: list[DroppedQuote]
    model_status: str | None
    model_score: int | None
    excerpt_paragraphs: int
    excerpt_chars: int
    served_model: str | None
    usage: dict[str, Any] | None
    error: str | None = None
    attempts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PrincipleResult":
        d = dict(d)
        d["quotes"] = [VerifiedQuote(**q) for q in d["quotes"]]
        d["dropped"] = [DroppedQuote(**q) for q in d["dropped"]]
        return cls(**d)


RETRY_SUFFIX = "\n\nReturn ONLY the JSON object now. Do not write any analysis before or after it."


def _parse(content: str) -> _Finding:
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)  # tolerate fenced output
    start, end = text.find("{"), text.rfind("}")
    if start > 0 and end > start:  # tolerate prose around the object
        text = text[start:end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Models often leave quote characters from the document unescaped. Repairing is safe here
        # because every quote is verified against the PDF afterwards; a mangled quote is dropped.
        data = json_repair.loads(text)
        if not isinstance(data, dict) or not data:
            raise
    return _Finding.model_validate(data)


def _clamp(status: str, score: int) -> int:
    lo, hi = SCORE_BANDS[status]
    return max(lo, min(hi, score))


def assess_principle(
    doc: Document,
    principle: Principle,
    client: ChatClient,
    verifier: QuoteVerifier | None = None,
    budget_chars: int | None = None,
) -> PrincipleResult:
    verifier = verifier or QuoteVerifier(doc)
    paragraphs = select_paragraphs(doc, principle, **({"budget_chars": budget_chars} if budget_chars else {}))
    excerpts = render_excerpts(paragraphs)
    user = (
        f"Principle: {principle.title} ({principle.key})\n"
        f"Question: {principle.question}\n\n"
        f"Document excerpts:\n{excerpts}"
    )

    finding: _Finding | None = None
    completion: Completion | None = None
    attempts: list[dict[str, Any]] = []
    error = None
    for attempt in (1, 2):  # one retry on invalid output
        prompt = user if attempt == 1 else user + RETRY_SUFFIX
        try:
            completion = client.complete_json(SYSTEM_PROMPT, prompt, "principle_finding", RESPONSE_SCHEMA, max_tokens=6000)
            attempts.append({"served_model": completion.served_model, "usage": completion.usage, "content": completion.content})
            finding = _parse(completion.content)
            break
        except (json.JSONDecodeError, ValidationError) as e:
            error = f"invalid output (attempt {attempt}): {e.__class__.__name__}: {e}"
            log.warning("%s %s", principle.key, error)
        except Exception as e:  # network / provider errors
            error = f"request failed (attempt {attempt}): {e.__class__.__name__}: {e}"
            attempts.append({"error": error})
            log.warning("%s %s", principle.key, error)

    base = dict(
        principle=principle.key,
        excerpt_paragraphs=len(paragraphs),
        excerpt_chars=len(excerpts),
        served_model=completion.served_model if completion else None,
        usage=completion.usage if completion else None,
        attempts=attempts,
    )
    if finding is None:
        # Not "no evidence": the document was never assessed, so this must not lower the score.
        return PrincipleResult(
            status="assessment_failed", score=None, rationale="Model output could not be used.", quotes=[],
            dropped_findings=0, dropped=[], model_status=None, model_score=None, error=error, **base,
        )

    verified: list[VerifiedQuote] = []
    dropped: list[DroppedQuote] = []
    for q in finding.quotes:
        check = verifier.check(q.text, q.paragraph_id)
        if check.verified:
            verified.append(VerifiedQuote(q.text, check.paragraph_id, check.page, check.method))
        else:
            dropped.append(DroppedQuote(q.text, q.paragraph_id, check.method))

    status = finding.status
    if not verified and status != "no_evidence":
        status = "no_evidence"  # a claim without a verifiable quote does not count
    score = None if status == "not_applicable" else _clamp(status, finding.score if status == finding.status else 0)

    return PrincipleResult(
        status=status,
        score=score,
        rationale=finding.rationale,
        quotes=verified,
        dropped_findings=len(dropped),
        dropped=dropped,
        model_status=finding.status,
        model_score=finding.score,
        **base,
    )
