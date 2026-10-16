"""Registry-side facts about a project from the CarbonPlan OffsetsDB snapshot."""

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from core.data import offsetsdb

STOP = {"project", "projects", "the", "of", "in", "by", "and", "at", "for", "on", "limited", "ltd", "pvt", "private",
        "grouped", "bundled", "programme", "program", "activity", "pa", "co", "company", "inc", "llc", "sa", "plc"}


@lru_cache(maxsize=1)
def _flows() -> pd.DataFrame:
    c = offsetsdb.credits()
    c = c[c.transaction_type.isin(["issuance", "retirement"])]
    return c.groupby(["project_id", "vintage", "transaction_type"]).quantity.sum().unstack(fill_value=0)


@lru_cache(maxsize=1)
def _projects() -> pd.DataFrame:
    return offsetsdb.projects().set_index("project_id")


def vintage_flows(project_id: str) -> dict[int, dict[str, float]]:
    """{vintage: {"issued": t, "retired": t}} from the snapshot's issuance and retirement records."""
    f = _flows()
    if project_id not in f.index.get_level_values(0):
        return {}
    sub = f.loc[project_id]
    return {int(v): {"issued": float(r.get("issuance", 0)), "retired": float(r.get("retirement", 0))}
            for v, r in sub.iterrows() if pd.notna(v)}


def registry_protocols(project_id: str) -> list[str]:
    p = _projects()
    if project_id not in p.index:
        return []
    protocol = p.loc[project_id, "protocol"]
    return [str(x).upper() for x in protocol] if protocol is not None and len(protocol) else []


def name_tokens(name: str) -> frozenset[str]:
    words = re.findall(r"[a-z0-9]+", name.lower())
    return frozenset(w for w in words if w not in STOP and len(w) > 1)


@lru_cache(maxsize=1)
def _idf() -> dict[str, float]:
    """Inverse document frequency of name words across all listed projects: 'solar' is common, 'bedford' rare."""
    names = [name_tokens(str(n)) for n in _projects()["name"]]
    df = Counter(w for ws in names for w in ws)
    return {w: math.log(len(names) / c) for w, c in df.items()}


def name_similarity(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity of two names' words, each word weighted by its rarity (unseen words count as rarest)."""
    idf = _idf()
    rarest = max(idf.values(), default=1.0)

    def weight(words: frozenset[str]) -> float:
        return sum(idf.get(w, rarest) for w in words)

    union = weight(a | b)
    return weight(a & b) / union if union else 0.0


@dataclass(frozen=True)
class SimilarListing:
    project_id: str
    registry: str
    name: str
    country: str | None
    similarity: float


def similar_listings(project_id: str, threshold: float = 0.6) -> list[SimilarListing]:
    """Other OffsetsDB projects in the same country whose names share most of their distinctive words.

    A match is a lead for a human, not proof of double listing: grouped programmes and phases of one site
    legitimately share names, and a renamed duplicate would not match."""
    p = _projects()
    if project_id not in p.index:
        return []
    me = p.loc[project_id]
    mine = name_tokens(str(me["name"]))
    if not mine:
        return []
    same_country = p[(p["country"] == me["country"]) & (p.index != project_id)]
    out = []
    for pid, row in same_country.iterrows():
        theirs = name_tokens(str(row["name"]))
        if not theirs:
            continue
        sim = name_similarity(mine, theirs)
        if sim >= threshold:
            out.append(SimilarListing(project_id=str(pid), registry=str(row["registry"]), name=str(row["name"]),
                                      country=row["country"], similarity=round(sim, 2)))
    return sorted(out, key=lambda s: -s.similarity)
