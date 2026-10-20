"""Deterministic data checks for one project: no model involved, every result traceable to a page or a record.

Each check returns one of
  pass           the data agree,
  flag           a discrepancy a reviewer should look at (a lead, not a finding of wrongdoing),
  info           context worth showing, no judgement,
  not_available  the input needed is missing (said plainly, never treated as a pass).
"""

from dataclasses import asdict
from datetime import date, timedelta
from typing import Any

from core.ai.pdf_extract import Table, extract_tables
from core.ai.sources import ROLES, ProjectSources
from core.checks import registry_data
from core.checks.estimates import EstimateTable, find_estimate_tables
from core.data import offsetsdb

SCHEMA = "checks-v2"
OVER_ESTIMATE = 1.2  # issued more than 20% above the document's own figures
UNDER_ESTIMATE = 0.5  # issued less than half: under-delivery, or a table of cumulative stocks


def _check(cid: str, title: str, status: str, summary: str, **details: Any) -> dict[str, Any]:
    return {"id": cid, "title": title, "status": status, "summary": summary, "details": details}


def document_coverage(project: ProjectSources) -> dict[str, Any]:
    cov = project.coverage()
    held = ", ".join(f"{ROLES[r]} ×{n}" for r, n in cov["held"].items())
    if not cov["missing"]:
        return _check("document_coverage", "Documents read", "pass", f"Read: {held}.", **cov)
    missing = ", ".join(ROLES[r] for r in cov["missing"])
    return _check("document_coverage", "Documents read", "flag",
                  f"Read: {held}. Not read: {missing}. Findings of 'no evidence' may only mean the evidence is in "
                  "a document that was not read.", **cov)


def _distinct(tables: list[tuple[str, EstimateTable]]) -> list[tuple[str, EstimateTable]]:
    seen, out = set(), []
    for f, e in tables:
        key = tuple(sorted(e.by_year.items()))
        if key not in seen:
            seen.add(key)
            out.append((f, e))
    return out


def _compare(e: EstimateTable, flows: dict[int, dict[str, float]]) -> dict[str, Any] | None:
    """Compare one yearly table with issuance, per vintage and over the table's whole span.

    The span total is the robust figure: registries sometimes book several years under one vintage, and
    partial years (the start or end of a crediting period) cannot be matched to a calendar-year vintage.
    The document side counts every full year of the table up to the last issued vintage; the registry side
    counts every vintage issued within the table's years. Counting the document's early years even when the
    registry booked them later keeps the ratio conservative."""
    issued = {v: x["issued"] for v, x in flows.items() if x["issued"] > 0}
    if not issued:
        return None
    full = {y: v for y, v in e.by_year.items() if y not in e.partial_years}
    doc_years = [y for y in full if y <= max(issued)]
    reg_years = [v for v in issued if min(e.by_year) <= v <= max(e.by_year) and v not in e.partial_years]
    if not doc_years or not reg_years:
        return None
    doc_sum = sum(full[y] for y in doc_years)
    reg_sum = sum(issued[v] for v in reg_years)
    per_vintage = [{"vintage": v, "document": full[v], "issued": issued[v], "ratio": round(issued[v] / full[v], 3)}
                   for v in sorted(full) if v in issued and full[v] > 0]
    return {"span": [min(doc_years + reg_years), max(doc_years + reg_years)],
            "document_sum": doc_sum, "issued_sum": reg_sum,
            "ratio": round(reg_sum / doc_sum, 3) if doc_sum else None, "per_vintage": per_vintage}


def issuance_vs_estimate(project: ProjectSources, tables: dict[str, list[Table]]) -> dict[str, Any]:
    title = "Issued credits vs the document's own yearly figures"
    # ex-ante figures: the project description (and supporting documents such as a CDM PDD), not the
    # monitoring or verification reports, whose figures issued_vs_monitored compares
    ex_ante = {f.local_path for f in project.files if f.role in ("project_description", "supporting")}
    found = _distinct([(f, e) for f, ts in tables.items() if f in ex_ante for e in find_estimate_tables(ts)])
    flows = registry_data.vintage_flows(project.project_id)
    if not found:
        return _check("issuance_vs_estimate", title, "not_available",
                      "No table of yearly net emission reductions could be read from the documents.")
    if not flows:
        return _check("issuance_vs_estimate", title, "not_available", "No issuance records in OffsetsDB.")

    candidates = []
    for file, e in found:
        candidates.append({"file": file, "table_id": e.table_id, "page": e.page, "column": e.column,
                           "rows_read": e.rows_text, "partial_years": sorted(e.partial_years),
                           "multi_year_rows": e.multi_year_rows, "document_total": e.total,
                           "comparison": _compare(e, flows)})
    comparable = [c for c in candidates if c["comparison"] and c["comparison"]["ratio"] is not None]
    if not comparable:
        return _check("issuance_vs_estimate", title, "not_available",
                      "The document's yearly figures do not overlap any issued vintage.", candidates=candidates)

    # Compare with the table that covers the most issued vintages; between equally complete tables (two
    # readings of the same years), take the one that best explains the issued volume.
    def coverage(c: dict[str, Any]) -> int:
        return len(c["comparison"]["per_vintage"])

    widest = max(coverage(c) for c in comparable)
    best = min((c for c in comparable if coverage(c) == widest), key=lambda c: c["comparison"]["ratio"])
    cmp_ = best["comparison"]
    limit = round((OVER_ESTIMATE - 1) * 100)
    where = f"table on page {best['page']}" + (f", one of {len(comparable)} tables" if len(comparable) > 1 else "")
    figures = (f"{cmp_['span'][0]}-{cmp_['span'][1]}: issued {cmp_['issued_sum']:,.0f} t, document "
               f"{cmp_['document_sum']:,.0f} t ({cmp_['ratio']:.2f}x, {where})")
    note = ("Ex-ante figures in a project description can legitimately differ from monitored results; the "
            "monitoring and verification reports explain the issued volume.")
    if cmp_["ratio"] > OVER_ESTIMATE:
        return _check("issuance_vs_estimate", title, "flag",
                      f"Issuance exceeds the document's own figures by more than {limit}% over {figures}. {note}",
                      ratio=cmp_["ratio"], candidates=candidates)
    if cmp_["ratio"] < UNDER_ESTIMATE:
        return _check("issuance_vs_estimate", title, "info",
                      f"Issuance is far below the document's figures ({figures}). Either the project delivered much "
                      "less than projected, or the table holds cumulative stocks rather than yearly figures (common "
                      "for afforestation projects); check the table.", ratio=cmp_["ratio"], candidates=candidates)
    over = [r["vintage"] for r in cmp_["per_vintage"] if r["ratio"] > OVER_ESTIMATE]
    if over:
        return _check("issuance_vs_estimate", title, "info",
                      f"Over the whole span issuance is within {limit}% of the document ({figures}), though single "
                      f"vintages exceed it ({', '.join(map(str, over))}).", ratio=cmp_["ratio"], candidates=candidates)
    return _check("issuance_vs_estimate", title, "pass", f"Issuance is within {limit}% of the document: {figures}.",
                  ratio=cmp_["ratio"], candidates=candidates)


MONITORED_TOLERANCE = 1.02  # issued may round a little above the monitored figure


def _period(text: str | None) -> tuple[date, date] | None:
    if not text or "/" not in text:
        return None
    a, b = text.split("/")
    return date.fromisoformat(a), date.fromisoformat(b)


def _covered(year: int, periods: list[tuple[date, date]]) -> bool:
    """True when every day of the calendar year lies inside the union of the monitoring periods."""
    day, end = date(year, 1, 1), date(year, 12, 31)
    for a, b in sorted(periods):
        if a <= day <= b:
            day = b + timedelta(days=1)
        if day > end:
            return True
    return False


def issuance_vs_monitored(project: ProjectSources, tables: dict[str, list[Table]]) -> dict[str, Any]:
    """Issued credits per vintage against the monitoring reports' own yearly net reductions.

    Only years inside a report's monitoring period are read from it (a report also repeats earlier periods and
    projects later ones); a report without a recorded period is skipped. Issuance at or below the monitored figure
    is expected (AFOLU projects deposit a buffer share). A vintage above it is flagged only when the monitoring
    reports read cover the whole calendar year; otherwise later periods may hold the rest.
    """
    title = "Issued credits vs the monitoring reports' figures"
    # a joint project description and monitoring report holds both ex-ante and monitored tables, which the
    # parser cannot tell apart, so only files registered as monitoring reports are read here
    reports = [f for f in project.by_role("monitoring_report") if f.role == "monitoring_report" and f.local_path in tables]
    if not reports:
        return _check("issuance_vs_monitored", title, "not_available", "No monitoring report was read.")
    flows = registry_data.vintage_flows(project.project_id)
    if not flows:
        return _check("issuance_vs_monitored", title, "not_available", "No issuance records in OffsetsDB.")
    periods, monitored, sources, skipped = [], {}, {}, []
    for f in sorted(reports, key=lambda f: f.period or ""):
        p = _period(f.period)
        if p is None:
            skipped.append(f"{f.file_name} (no monitoring period recorded)")
            continue
        periods.append(p)
        for e in find_estimate_tables(tables[f.local_path]):
            values = {y: v for y, v in e.by_year.items() if p[0].year <= y <= p[1].year and v > 0}
            for y, v in values.items():  # the latest report covering a year wins
                monitored[y] = v
                sources[y] = {"file": f.local_path, "page": e.page, "table_id": e.table_id,
                              "partial_row": y in e.partial_years}
    issued = {v: x["issued"] for v, x in flows.items() if x["issued"] > 0}
    rows = [{"vintage": y, "monitored": monitored[y], "issued": issued[y], "ratio": round(issued[y] / monitored[y], 3),
             # a row for part of a year (e.g. "01-January-2024 - 31-January-2024") is never the whole year's figure
             "whole_year_monitored": _covered(y, periods) and not sources[y]["partial_row"], **sources[y]}
            for y in sorted(monitored) if y in issued]
    if not rows:
        return _check("issuance_vs_monitored", title, "not_available",
                      "No yearly net-reduction table in the monitoring reports read overlaps an issued vintage"
                      + (f"; skipped {'; '.join(skipped)}" if skipped else "") + ".", skipped=skipped)
    over = [r for r in rows if r["ratio"] > MONITORED_TOLERANCE]
    flagged = [r for r in over if r["whole_year_monitored"]]
    span = f"{rows[0]['vintage']}-{rows[-1]['vintage']}" if len(rows) > 1 else str(rows[0]["vintage"])
    ratios = ", ".join(f"{r['vintage']}: {r['ratio']:.2f}" for r in rows)
    if flagged:
        return _check("issuance_vs_monitored", title, "flag",
                      "Issuance exceeds the monitored net reductions for vintages the monitoring reports fully cover ("
                      + ", ".join(f"{r['vintage']}: issued {r['issued']:,.0f} t vs monitored {r['monitored']:,.0f} t"
                                  for r in flagged) + ").", vintages=rows, skipped=skipped)
    ok = [r for r in rows if r["ratio"] <= MONITORED_TOLERANCE]
    summary = (f"Issued credits per vintage over monitored net reductions ({span}): {ratios}. "
               f"{len(ok)} of {len(rows)} vintages are at or below the monitored figure (a ratio below 1 is expected "
               "where a buffer share is withheld).")
    if over:
        summary += (" Above it: " + ", ".join(str(r["vintage"]) for r in over)
                    + ", a vintage the monitoring reports read cover only in part, so a later period may hold the rest.")
        return _check("issuance_vs_monitored", title, "info", summary, vintages=rows, skipped=skipped)
    return _check("issuance_vs_monitored", title, "pass", summary, vintages=rows, skipped=skipped)


def retired_vs_issued(project: ProjectSources) -> dict[str, Any]:
    title = "Retirements never exceed issuance"
    flows = registry_data.vintage_flows(project.project_id)
    if not flows:
        return _check("retired_vs_issued", title, "not_available", "No records in OffsetsDB.")
    over = [{"vintage": v, "issued": x["issued"], "retired": x["retired"], "excess": x["retired"] - x["issued"]}
            for v, x in sorted(flows.items()) if x["retired"] > x["issued"]]
    if over:
        return _check("retired_vs_issued", title, "flag",
                      "More credits retired than issued for vintage "
                      + ", ".join(f"{o['vintage']} (+{o['excess']:,.0f} t)" for o in over)
                      + ". Likely a data inconsistency in the registry records; worth a reconciliation.",
                      vintages=over)
    return _check("retired_vs_issued", title, "pass",
                  f"Across {len(flows)} vintages, retired volume never exceeds issued volume.")


def methodology_matches_registry(project: ProjectSources) -> dict[str, Any]:
    title = "Methodology matches the registry listing"
    listed = registry_data.registry_protocols(project.project_id)
    ours = project.methodology.upper()
    if not listed:
        return _check("methodology_matches_registry", title, "not_available",
                      f"OffsetsDB lists no methodology for this project; the document states {ours}.")
    if ours in listed:
        return _check("methodology_matches_registry", title, "pass", f"Document and registry both give {ours}.",
                      registry=listed)
    return _check("methodology_matches_registry", title, "flag",
                  f"The document states {ours}; the registry lists {', '.join(listed)}.", registry=listed)


def similar_listings(project: ProjectSources) -> dict[str, Any]:
    title = "Similar listings in other registries or programmes"
    mine = registry_data.vintage_flows(project.project_id)
    found = []
    for s in registry_data.similar_listings(project.project_id):
        theirs = registry_data.vintage_flows(s.project_id)
        both = sorted(v for v in mine if v in theirs and mine[v]["issued"] > 0 and theirs[v]["issued"] > 0)
        found.append({**asdict(s), "vintages_issued_in_both": both})
    if not found:
        return _check("similar_listings", title, "pass",
                      "No project in the same country with a closely matching name.")
    overlapping = [f for f in found if f["vintages_issued_in_both"]]
    if overlapping:
        f = overlapping[0]
        return _check("similar_listings", title, "flag",
                      f"{f['project_id']} ({f['registry']}) has a similar name ('{f['name']}') and issued credits for "
                      f"the same vintages ({', '.join(map(str, f['vintages_issued_in_both']))}). A name match is a "
                      "lead, not proof: check whether these are the same activity.", listings=found)
    return _check("similar_listings", title, "info",
                  f"{len(found)} similarly named project(s), with no vintage issued in both: "
                  + "; ".join(f"{f['project_id']} ({f['registry']})" for f in found) + ".", listings=found)


def run_checks(project: ProjectSources, tables: dict[str, list[Table]] | None = None) -> dict[str, Any]:
    """All checks for one project. ``tables`` maps each file's local path to its tables (read if omitted)."""
    files = [f for f in project.files if f.status() == "present"]
    if tables is None:
        tables = {f.local_path: extract_tables(f.path) for f in files}
    return {
        "schema": SCHEMA,
        "project_id": project.project_id,
        "inputs": {"documents": [{"role": f.role, "file": f.local_path, "sha256": f.sha256} for f in files],
                   "offsetsdb_snapshot": offsetsdb.snapshot_date()},
        "checks": [document_coverage(project), issuance_vs_estimate(project, tables),
                   issuance_vs_monitored(project, tables), retired_vs_issued(project),
                   methodology_matches_registry(project), similar_listings(project)],
    }
