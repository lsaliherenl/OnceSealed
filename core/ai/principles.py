"""The ICVCM Core Carbon Principles we assess from project documents.

ICVCM defines ten principles (https://icvcm.org/?p=2349). We score the five
that a project document can evidence; program-level principles (governance,
tracking, independent verification, transparency) and net-zero alignment /
sustainable development impacts are out of scope.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Principle:
    key: str
    title: str
    question: str
    keywords: tuple[str, ...]
    weight: float


PRINCIPLES: tuple[Principle, ...] = (
    Principle(
        key="additionality",
        title="Additionality",
        question=(
            "Does the document demonstrate that the mitigation activity would not have happened "
            "without carbon credit revenue? Look for investment analysis (IRR vs benchmark), barrier "
            "analysis, common practice analysis, regulatory surplus and the baseline scenario."
        ),
        keywords=(
            "additionality", "additional", "investment analysis", "barrier", "common practice",
            "regulatory surplus", "benchmark", "irr", "financial analysis", "baseline scenario",
            "without the project", "carbon revenue", "sensitivity analysis",
        ),
        weight=0.25,
    ),
    Principle(
        key="permanence",
        title="Permanence",
        question=(
            "Is the risk that emission reductions or removals are reversed identified and managed? "
            "Look for non-permanence risk assessment, buffer pool contributions, reversal monitoring "
            "and long-term commitments. If the activity type has no material reversal risk (e.g. "
            "avoided grid emissions), say so with evidence of the activity type."
        ),
        keywords=(
            "permanence", "non-permanence", "reversal", "buffer", "risk rating", "risk report",
            "risk assessment", "fire", "natural risk", "long-term", "project longevity",
        ),
        weight=0.20,
    ),
    Principle(
        key="robust_quantification",
        title="Robust and conservative quantification",
        question=(
            "Are emission reductions quantified robustly and conservatively? Look for baseline and "
            "project emission calculations, leakage, emission factors, uncertainty treatment, "
            "conservative choices, and a monitoring plan with QA/QC."
        ),
        keywords=(
            "baseline emissions", "project emissions", "leakage", "emission factor", "conservative",
            "uncertainty", "monitoring plan", "qa/qc", "quality assurance", "calculation",
            "measured", "monitoring", "net emission reductions",
        ),
        weight=0.25,
    ),
    Principle(
        key="no_double_counting",
        title="No double counting",
        question=(
            "Is it shown that the reductions are counted only once? Look for statements on "
            "registration under other GHG programs, other environmental credits (e.g. RECs / I-RECs), "
            "emissions trading schemes, double issuance and corresponding adjustments."
        ),
        keywords=(
            "double counting", "double issuance", "double claiming", "other ghg program",
            "other forms of environmental credit", "environmental credit", "emissions trading",
            "renewable energy certificate", "i-rec", "rec ", "cdm", "corresponding adjustment",
            "not registered", "participation under other",
        ),
        weight=0.15,
    ),
    Principle(
        key="safeguards",
        title="Social and environmental safeguards",
        question=(
            "Are social and environmental risks assessed and mitigated? Look for stakeholder "
            "consultation, free prior and informed consent, grievance mechanisms, environmental "
            "impact assessment, biodiversity, indigenous peoples and local communities, labour and "
            "gender."
        ),
        keywords=(
            "stakeholder", "consultation", "local communities", "indigenous", "free, prior and informed",
            "fpic", "grievance", "environmental impact", "biodiversity", "human rights", "gender",
            "labour", "labor", "safeguard", "community",
        ),
        weight=0.15,
    ),
)

BY_KEY = {p.key: p for p in PRINCIPLES}
