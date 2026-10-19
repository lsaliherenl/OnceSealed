"""Ask the evidence checklist (core.ai.checklist) of a model, on one excerpt.

The same code answers the checklist in the evaluation (scripts/run_checklist_models.py, scored against the
labelled gold set) and in the published reports (core.ai.report), so the measured accuracy is the accuracy of
what is published.

* ``LLMChecklist``: yes/no per question plus the id of the paragraph holding the evidence. A "yes" must cite a
  paragraph of the excerpt (EVIDENCE_RULE): if the first answer cites none, the model is asked once more for the
  paragraph; a "yes" still without one is published as "no" and counted as dropped.
* ``JevChecklist``: probability of "yes" per question from the decision model, used as a second opinion.
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import json_repair

from core.ai.checklist import BY_PRINCIPLE, Question
from core.ai.client import ChatClient
from core.ai.decision import JevDecisionModel
from core.ai.pdf_extract import Paragraph

CHECKLIST_PROMPT_VERSION = "checklist-v1"
EVIDENCE_RULE = "yes-cites-excerpt-paragraph-v2"

LLM_SYSTEM = """You check whether specific kinds of evidence are present in an excerpt of a carbon project document.
Answer each question about the excerpt ONLY: "yes" if the excerpt itself contains that evidence, otherwise "no".
Do not use outside knowledge and do not guess what the rest of the document says.
For every "yes", give the id of the paragraph (shown in square brackets) that contains the evidence.
Respond with JSON only."""

RETRY_NOTE = "\n\nReturn ONLY the JSON object with one answer per question id."

EVIDENCE_NOTE = ("\n\nYou answered \"yes\" to the questions below without citing a paragraph. For each one, give the id "
                 "of the paragraph that contains the evidence, exactly as shown in square brackets, or \"none\" if no "
                 "paragraph does.\n")


def citation_schema(question_ids: list[str], paragraph_ids: list[str]) -> dict[str, Any]:
    """Follow-up answer format: one paragraph id per question, restricted to the excerpt's ids (or "none")."""
    return {
        "type": "object", "additionalProperties": False, "required": ["citations"],
        "properties": {"citations": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["id", "paragraph_id"],
            "properties": {"id": {"type": "string", "enum": question_ids},
                           "paragraph_id": {"type": "string", "enum": paragraph_ids + ["none"]}}}}},
    }

LLM_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["answers"],
    "properties": {"answers": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "answer", "evidence"],
        "properties": {"id": {"type": "string"}, "answer": {"type": "string", "enum": ["yes", "no"]},
                       "evidence": {"type": ["string", "null"]}}}}},
}

PARAGRAPH_ID = re.compile(r"(?:x\d+-)?p\d+-\d+")


def excerpt_lines(paragraphs: list[Paragraph]) -> list[str]:
    return [f"[{p.id}] {' '.join(p.text.split())}" for p in paragraphs] or ["(no relevant paragraphs)"]


def evidence_ids(raw: str | None, valid: set[str]) -> list[str]:
    """Paragraph ids cited in a model's evidence field that exist in the excerpt ('.p15-03, p9-04' -> ids)."""
    seen: list[str] = []
    for m in PARAGRAPH_ID.finditer(raw or ""):
        if m.group(0) in valid and m.group(0) not in seen:
            seen.append(m.group(0))
    return seen


def parse_answers(content: str) -> dict[str, dict[str, Any]]:
    text = content.strip()
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = json_repair.loads(text)
    try:
        return {a["id"]: a for a in data["answers"]}
    except (KeyError, TypeError):
        return {}


def parse_citations(content: str) -> dict[str, str]:
    text = content.strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        data = json_repair.loads(text[start:end + 1])
        return {c["id"]: c["paragraph_id"] for c in data["citations"]}
    except (KeyError, TypeError, ValueError):
        return {}


@dataclass
class Answer:
    question: str
    answer: str | None              # "yes" | "no" | None (model gave no usable answer)
    evidence: list[str] = field(default_factory=list)
    model_said: str | None = None   # the model's own answer before the evidence rule
    dropped: str | None = None      # why a "yes" was not published


@dataclass
class ChecklistResult:
    answers: dict[str, Answer]
    served_model: str | None
    latency_ms: int
    cost: float
    calls: int


class Checklist(Protocol):
    name: str

    def answer(self, principle: str, paragraphs: list[Paragraph]) -> ChecklistResult: ...


class LLMChecklist:
    def __init__(self, client: ChatClient | None = None):
        self.client = client or ChatClient()
        self.name = self.client.settings.model

    def _ask(self, prompt: str) -> tuple[dict[str, dict[str, Any]], Any]:
        # The model reasons before answering (often 2-3k tokens); a lower limit can cut the answer off entirely.
        out = self.client.complete_json(LLM_SYSTEM, prompt, "checklist_answers", LLM_SCHEMA, max_tokens=8000)
        return parse_answers(out.content), out

    def answer(self, principle: str, paragraphs: list[Paragraph]) -> ChecklistResult:
        qs: list[Question] = BY_PRINCIPLE[principle]
        valid = {p.id for p in paragraphs}
        user = ("Excerpt:\n" + "\n\n".join(excerpt_lines(paragraphs)) + "\n\nQuestions:\n"
                + "\n".join(f"{q.id}: {q.text}" for q in qs))
        t0 = time.perf_counter()
        raw: dict[str, dict[str, Any]] = {}
        cost, calls, out = 0.0, 0, None
        for attempt in range(3):  # retry when the output cannot be parsed or answers are missing
            raw, out = self._ask(user if attempt == 0 else user + RETRY_NOTE)
            cost += (out.usage or {}).get("cost") or 0
            calls += 1
            if all(q.id in raw and raw[q.id].get("answer") in ("yes", "no") for q in qs):
                break
        answers = {}
        for q in qs:
            said = raw.get(q.id, {}).get("answer")
            said = said if said in ("yes", "no") else None
            answers[q.id] = Answer(q.id, said, evidence_ids(raw.get(q.id, {}).get("evidence"), valid), model_said=said)

        missing = [q for q in qs if answers[q.id].answer == "yes" and not answers[q.id].evidence]
        if missing and paragraphs:
            follow = user + EVIDENCE_NOTE + "\n".join(f"{q.id}: {q.text}" for q in missing)
            schema = citation_schema([q.id for q in missing], [p.id for p in paragraphs])
            cited: dict[str, str] = {}
            for _ in range(2):  # a second try only when the reply could not be read
                out2 = self.client.complete_json(LLM_SYSTEM, follow, "evidence_citations", schema, max_tokens=8000)
                cost += (out2.usage or {}).get("cost") or 0
                calls += 1
                cited = parse_citations(out2.content)
                if cited:
                    break
            for q in missing:
                answers[q.id].evidence = evidence_ids(cited.get(q.id), valid)
        for a in answers.values():
            if a.answer == "yes" and not a.evidence:
                a.answer, a.dropped = "no", "no_paragraph_cited"
        return ChecklistResult(answers, getattr(out, "served_model", None),
                               round((time.perf_counter() - t0) * 1000), cost, calls)


class JevChecklist:
    """The decision model's probability of "yes"; answer = p_yes >= 0.5. No evidence ids."""

    def __init__(self, jev: JevDecisionModel | None = None):
        self.jev = jev or JevDecisionModel()
        self.name = self.jev.name

    def probabilities(self, principle: str, paragraphs: list[Paragraph]) -> tuple[dict[str, float], dict[str, Any]]:
        qs = BY_PRINCIPLE[principle]
        body = {"model": self.jev.name, "state": excerpt_lines(paragraphs), "questions": {
            q.id: {"type": "noul", "instructions": q.text + " Judge only the text provided; answer about this excerpt."}
            for q in qs}}
        data = self.jev._post(body)
        return {q.id: float(data["answers"][q.id]["noul"]) for q in qs}, data
