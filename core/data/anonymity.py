"""How often is the end beneficiary of a carbon credit retirement identifiable? (OffsetsDB)

Each retirement is put in exactly one class, checked in this order:

    explicitly_undisclosed  beneficiary or note says so ("not disclosed", "not public", "anonymous", "private offset")
    intermediary_only       only a reseller / platform is named ("4air client", "customers of pledge")
    named                   a beneficiary is named (raw field or CarbonPlan's harmonized field)
    named_in_note           no beneficiary field, but the note names one ("retired on behalf of X", "order ... for X")
    generic_note            only free text without a beneficiary ("environmental benefit")
    no_information          beneficiary, harmonized beneficiary and note are all empty

"Identifiable" = `named` or `named_in_note`; everything else is not identifiable. Markers are matched exactly or as whole
phrases so that company names such as "XYZ Private Limited" are not counted as anonymous.
`retirement_account` is ignored: it names the account holder (often a broker), not the beneficiary.
"""

import re

import pandas as pd

CLASSES = ["named", "named_in_note", "intermediary_only", "explicitly_undisclosed", "generic_note", "no_information"]
IDENTIFIABLE = ["named", "named_in_note"]
NOT_IDENTIFIABLE = [c for c in CLASSES if c not in IDENTIFIABLE]

UNDISCLOSED_EXACT = {
    "not disclosed", "not public", "anonymous", "anonymously", "undisclosed", "confidential", "private",
    "private offset", "-", ".", "n/a", "na", "none", "unknown", "not specified", "not provided",
    "individual(s) or private person",
}
UNDISCLOSED_PHRASE = re.compile(
    r"\bfor anonymous\b|\bon behalf of anonymous\b|^anonymous\b|\bretire anonymously\b|\bprivate compensation\b")
NAMED_IN_NOTE = re.compile(
    r"\bon behalf of\b|\bretired (?:for|by)\b|\border \S+ for\b|\boffset(?:ting)? for\b|\bcompensat\w* (?:for|of)\b")
INTERMEDIARY = re.compile(
    r"\bclients?\b|\bcustomers?\b|\bend[- ]users?\b|\bon behalf of (?:its|their|our) (?:clients|customers|users)\b")


def _clean(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip().str.lower()


def classify(retirements: pd.DataFrame) -> pd.Series:
    ben = _clean(retirements["retirement_beneficiary"])
    harm = _clean(retirements["retirement_beneficiary_harmonized"])
    note = _clean(retirements["retirement_note"])

    undisclosed = (ben.isin(UNDISCLOSED_EXACT) | note.isin(UNDISCLOSED_EXACT)
                   | ben.str.contains(UNDISCLOSED_PHRASE) | note.str.contains(UNDISCLOSED_PHRASE))
    intermediary = (ben.str.contains(INTERMEDIARY) | harm.str.contains(INTERMEDIARY)
                    | ((ben == "") & note.str.contains(INTERMEDIARY)))
    named = (ben != "") | (harm != "")
    has_note = note != ""
    named_in_note = has_note & note.str.contains(NAMED_IN_NOTE)

    out = pd.Series("no_information", index=retirements.index)
    out[has_note] = "generic_note"
    out[named_in_note] = "named_in_note"
    out[named] = "named"
    out[intermediary] = "intermediary_only"
    out[undisclosed] = "explicitly_undisclosed"
    return out


def shares(df: pd.DataFrame, by: str | None = None, weight: str | None = "quantity") -> pd.DataFrame:
    """Share of each class, weighted by tonnes (default) or by row count (weight=None)."""
    w = df[weight] if weight else pd.Series(1.0, index=df.index)
    if by is None:
        t = w.groupby(df["class"]).sum()
        return (t / t.sum()).reindex(CLASSES, fill_value=0).to_frame("share").T
    t = (w.groupby([df[by], df["class"]], observed=True).sum().unstack(fill_value=0)
         .reindex(columns=CLASSES, fill_value=0))
    out = t.div(t.sum(axis=1), axis=0)
    out["total"] = t.sum(axis=1)
    return out


def retirements_with_class(credits: pd.DataFrame) -> pd.DataFrame:
    r = credits[credits["transaction_type"] == "retirement"].copy()
    r["class"] = classify(r)
    r["identifiable"] = r["class"].isin(IDENTIFIABLE)
    return r
