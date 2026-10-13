"""Layer 3: probabilistic judgement of evidence sufficiency.

The decision model sits behind the ``DecisionModel`` protocol so that Jev 1.13
(TypeSafe, via OpenRouter) can later be swapped for Turnike or any other model
that answers the same question set. The question set is versioned and shared:
change ``QUESTION_SET_VERSION`` whenever a question or option changes.
"""

import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

import core.config  # noqa: F401  (loads .env)
from core.ai.principles import Principle

QUESTION_SET_VERSION = "qs-v1"

EVIDENCE_LEVELS: dict[str, str] = {
    "quantified_verifiable": "Specific figures, data or analysis that a third party could check",
    "documentary": "Concrete description of procedures or facts, but not quantified or checkable",
    "assertion_only": "The proponent asserts compliance without supporting detail",
    "not_addressed": "The excerpts do not address this principle",
}

STRENGTH_LEVELS: list[str] = [
    "No evidence",
    "Assertion only",
    "Partial documentary evidence",
    "Strong, specific, checkable evidence",
]
STRENGTH_STATUS: list[str] = ["no_evidence", "assertion_only", "partial_evidence", "strong_evidence"]

# Strength level each evidence_level choice implies; used to spot disagreement between the two questions.
EVIDENCE_LEVEL_TO_STRENGTH: dict[str, int] = {
    "not_addressed": 0, "assertion_only": 1, "documentary": 2, "quantified_verifiable": 3,
}


def build_questions(principle: Principle) -> dict[str, Any]:
    topic = f"{principle.title.lower()}: {principle.question}"
    return {
        "evidence_level": {
            "type": "choice",
            "instructions": f"These are verbatim excerpts from a carbon project document. How well do they evidence {topic}",
            "criteria": EVIDENCE_LEVELS,
        },
        "independent": {
            "type": "noul",
            "instructions": "Does the evidence rely on independent sources (third-party data, audits, regulators) "
                            "rather than only the project proponent's own statements?",
        },
        "strength": {
            "type": "score",
            "instructions": f"Rate the strength of the evidence for {principle.title.lower()}.",
            "criteria": STRENGTH_LEVELS,
        },
    }


@dataclass
class Decision:
    evidence_level: str
    evidence_probabilities: dict[str, float]
    evidence_confidence: float
    independent: float
    strength: float  # 0 .. len(STRENGTH_LEVELS) - 1, may fall between levels
    strength_probabilities: dict[str, float]
    strength_confidence: float
    model: str
    question_set_version: str = QUESTION_SET_VERSION
    usage: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> int:
        """Strength mapped to 0-100 for the on-chain score."""
        return round(100 * self.strength / (len(STRENGTH_LEVELS) - 1))

    @property
    def status(self) -> str:
        """Strength rounded to the nearest level, so the label always agrees with ``score``."""
        level = min(max(math.floor(self.strength + 0.5), 0), len(STRENGTH_STATUS) - 1)  # half rounds up
        return STRENGTH_STATUS[level]

    @property
    def questions_disagree(self) -> bool:
        """Evidence-level choice and strength rating are two or more levels apart."""
        implied = EVIDENCE_LEVEL_TO_STRENGTH[self.evidence_level]
        return abs(implied - STRENGTH_STATUS.index(self.status)) >= 2


class DecisionModel(Protocol):
    name: str

    def decide(self, principle: Principle, evidence: list[str]) -> Decision: ...


class DecisionError(RuntimeError):
    pass


class JevDecisionModel:
    """TypeSafe Jev 1.13 through OpenRouter's decisions endpoint."""

    def __init__(self, model: str | None = None, url: str | None = None, api_key: str | None = None,
                 timeout: float = 60.0, retries: int = 3):
        self.name = model or os.environ.get("DECISION_MODEL", "typesafe/jev-1.13")
        self.url = url or os.environ.get("DECISION_URL", "https://openrouter.ai/api/alpha/decisions")
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set in .env")
        self.timeout, self.retries = timeout, retries

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "X-Title": "OnceSealed"}
        for attempt in range(self.retries):
            resp = httpx.post(self.url, json=body, headers=headers, timeout=self.timeout)
            if resp.status_code in (429, 503, 529) and attempt + 1 < self.retries:
                time.sleep(2 ** attempt)  # rate limited / overloaded: back off and retry
                continue
            if resp.status_code != 200:
                raise DecisionError(f"{resp.status_code}: {resp.text[:300]}")
            return resp.json()
        raise DecisionError("retries exhausted")

    def decide(self, principle: Principle, evidence: list[str]) -> Decision:
        body = {"model": self.name, "state": evidence, "questions": build_questions(principle)}
        return parse_decision(self._post(body))


def parse_decision(data: dict[str, Any]) -> Decision:
    a = data["answers"]
    ev, ind, st = a["evidence_level"], a["independent"], a["strength"]
    return Decision(
        evidence_level=ev["choice"],
        evidence_probabilities=ev["probabilities"],
        evidence_confidence=ev["confidence"],
        independent=ind["noul"],
        strength=st["score"],
        strength_probabilities=st["probabilities"],
        strength_confidence=st["confidence"],
        model=data.get("model", "unknown"),
        usage=data.get("usage", {}),
    )
