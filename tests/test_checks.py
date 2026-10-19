"""Deterministic data checks: estimate-table parsing, the issuance comparison and name matching.

The tables reproduce layouts met in the evaluation PDFs (merged header cells, date ranges wrapped over several
rows, a template table, "Total number of crediting years"), so the tests run without the PDFs or OffsetsDB.
"""

import json

import pytest

from core.ai.pdf_extract import Table
from core.ai.sources import load_manifest
from core.checks import registry_data, run
from core.checks.estimates import find_estimate_tables, parse_number, read_estimate_table


def t(rows, tid="p19-t1", page=19):
    return Table(id=tid, page=page, rows=rows)


# Header labels and numbers sit in different columns (merged cells), as in VCS138's PD.
MERGED = t([
    ["Year", "", "Estimated", "", "", "Estimated", "", "Estimated leakage emissions", "", "Estimated net", ""],
    ["", "", "baseline emissions", "", "", "project emissions", "", "", "", "GHG emission reductions", ""],
    ["2016 (March 29 - December 31)", "67360", "", "", "3", "", "", "0", "67357", "", ""],
    ["2017", "88441", "", "", "4", "", "", "0", "88437", "", ""],
    ["2018", "88441", "", "", "4", "", "", "0", "88437", "", ""],
    ["Total", "245,000", "", "", "11", "", "", "0", "244,231", "", ""],
    ["Total number of crediting years", "10", "", "", "", "", "", "", "", "", ""],
])


def test_parse_number_formats():
    assert parse_number("1,422,028") == 1422028
    assert parse_number("2,087,787.68") == 2087787.68
    assert parse_number("1.422.028") == 1422028
    assert parse_number("4") == 4
    for text in ("-", "10%", "n/a", "", "2016 (March)"):
        assert parse_number(text) is None


def test_merged_header_cells_pair_labels_and_numbers_in_order():
    e = read_estimate_table(MERGED)
    assert e.by_year == {2016: 67357, 2017: 88437, 2018: 88437}
    assert "net" in e.column.lower()
    assert e.total == 244231  # not the "Total number of crediting years" row
    assert e.partial_years == {2016}


def test_date_range_wrapped_over_rows_is_one_record():
    table = t([
        ["Year", "", "", "Estimated baseline emissions", "Estimated project emissions", "", "Estimated", "", "",
         "Estimated net GHG emission reductions", ""],
        ["", "05-August-", "", "170,354", "13,952", "7,504", "", "", "148,898", "", ""],
        ["", "2020-31-", "", "", "", "", "", "", "", "", ""],
        ["", "December-2020", "", "", "", "", "", "", "", "", ""],
        ["", "01-January-2021-", "", "417,311", "34,179", "18,382", "", "", "364,750", "", ""],
        ["", "31-December-2021", "", "", "", "", "", "", "", "", ""],
    ])
    e = read_estimate_table(table)
    assert e.by_year == {2020: 148898, 2021: 364750}
    assert e.partial_years == {2020}  # 5 August to 31 December; 2021 runs 1 January to 31 December


def test_template_table_with_only_baseline_values_is_rejected():
    template = t([
        ["", "Years", "", "Estimated baseline emissions", "", "Estimated project emissions", "", "Estimated leakage",
         "", "Estimated net GHG emission reductions or removals"],
        ["", "2009", "", "1,834,510.1", "", "", "", "", "", ""],
        ["", "2010", "", "1,960,580.9", "", "", "", "", "", ""],
        ["Etc...", "", "", "", "", "", "", "", "", ""],
    ])
    assert read_estimate_table(template) is None


def test_cumulative_and_unrelated_tables_are_skipped():
    cumulative = t([["Year", "Cumulative net GHG removals (t)"], ["2009", "932,951"], ["2010", "1,001,186"]])
    unrelated = t([["Year", "Rainfall (mm)"], ["2009", "1,200"], ["2010", "1,350"]])
    assert find_estimate_tables([cumulative, unrelated]) == []


@pytest.fixture
def project():
    return next(p for p in load_manifest() if p.project_id == "VCS985")


def _flows(monkeypatch, issued):
    monkeypatch.setattr(registry_data, "vintage_flows",
                        lambda pid: {v: {"issued": q, "retired": 0.0} for v, q in issued.items()})


def _yearly(values):
    return t([["Year", "Estimated net GHG emission reductions (tCO2e)"]] + [[str(y), f"{v:,}"] for y, v in values.items()])


def test_issuance_far_above_every_reading_is_flagged(monkeypatch, project):
    _flows(monkeypatch, {2012: 5_000_000, 2013: 2_000_000})
    out = run.issuance_vs_estimate(project, {"pd.pdf": [_yearly({2011: 1_000_000, 2012: 1_000_000, 2013: 1_000_000})]})
    assert out["status"] == "flag"
    # the document's 2011 counts too: the registry may book several years under one vintage
    assert out["details"]["ratio"] == pytest.approx(7_000_000 / 3_000_000, abs=1e-3)


def test_single_vintage_spikes_within_the_span_are_info(monkeypatch, project):
    _flows(monkeypatch, {2017: 80_000, 2018: 130_000, 2019: 70_000})
    out = run.issuance_vs_estimate(project, {"pd.pdf": [_yearly({2017: 90_000, 2018: 90_000, 2019: 90_000})]})
    assert out["status"] == "info" and "2018" in out["summary"]


def test_far_below_is_info_not_pass(monkeypatch, project):
    _flows(monkeypatch, {2012: 100_000, 2013: 100_000})
    out = run.issuance_vs_estimate(project, {"pd.pdf": [_yearly({2012: 900_000, 2013: 1_000_000})]})
    assert out["status"] == "info" and "cumulative" in out["summary"]


def test_missing_inputs_are_never_a_pass(monkeypatch, project):
    _flows(monkeypatch, {2012: 100_000})
    assert run.issuance_vs_estimate(project, {"pd.pdf": []})["status"] == "not_available"
    _flows(monkeypatch, {})
    assert run.issuance_vs_estimate(project, {"pd.pdf": [_yearly({2012: 1, 2013: 1})]})["status"] == "not_available"


def test_retired_above_issued_is_flagged(monkeypatch, project):
    monkeypatch.setattr(registry_data, "vintage_flows", lambda pid: {
        2016: {"issued": 100.0, "retired": 100.0}, 2017: {"issued": 100.0, "retired": 130.0}})
    out = run.retired_vs_issued(project)
    assert out["status"] == "flag" and out["details"]["vintages"][0]["excess"] == 30


def test_rare_shared_words_make_a_name_match_and_common_ones_do_not(monkeypatch):
    idf = {"renewable": 0.5, "solar": 0.4, "power": 0.3, "renew": 6.0, "adani": 6.0, "greater": 4.0, "new": 1.0,
           "bedford": 8.0, "lfg": 5.0, "utilization": 3.0}
    monkeypatch.setattr(registry_data, "_idf", lambda: idf)
    tok = registry_data.name_tokens
    same = registry_data.name_similarity(tok("Greater New Bedford LFG Utilization Project"), tok("Greater New Bedford LFG"))
    generic = registry_data.name_similarity(tok("Renewable Solar Power Project by ReNew Solar Power Private Limited"),
                                            tok("Renewable Solar Power Project by Adani"))
    assert same > 0.8 and generic < 0.2


def test_coverage_names_the_documents_not_read(tmp_path):
    manifest = {"documents": [{
        "project_id": "VCS1", "project_name": "X", "registry_url": "u", "methodology": "ACM0002",
        "doc_type": "VCS Project Description (joint PD/MR)", "file_name": "a.pdf", "local_path": "samples/pdfs/a.pdf",
        "sha256": "00", "covers": ["monitoring_report"],
        "extra_files": [{"role": "verification_report", "doc_type": "Verification report", "file_name": "b.pdf",
                         "local_path": "samples/pdfs/b.pdf", "sha256": "11"}]}]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    (p,) = load_manifest(path)
    cov = p.coverage()
    assert cov["held"] == {"project_description": 1, "monitoring_report": 1, "verification_report": 1}
    assert cov["missing"] == ["validation_report"]
    assert p.files[1].status() == "missing"  # not downloaded


def test_table_renders_row_by_row():
    assert t([["Year", "", "Net"], ["2017", "", "562,006"]]).render() == "Year | Net\n2017 | 562,006"


def _with_reports(project, *periods):
    """The project with monitoring reports covering the given periods (files need not exist)."""
    from dataclasses import replace
    from core.ai.sources import SourceFile
    mrs = [SourceFile(project.project_id, "monitoring_report", "MR", f"mr{i}.pdf", f"mr{i}.pdf", None, period=p)
           for i, p in enumerate(periods)]
    return replace(project, files=[project.files[0], *mrs])


def test_issuance_at_or_below_monitored_passes(monkeypatch, project):
    _flows(monkeypatch, {2013: 1_000_000, 2014: 900_000})
    p = _with_reports(project, "2012-08-08/2014-08-07", "2014-08-08/2015-08-07")
    # the second report repeats 2013 with another figure: years outside a report's own period are ignored
    out = run.issuance_vs_monitored(p, {"mr0.pdf": [_yearly({2013: 1_000_000, 2014: 1_000_000})],
                                        "mr1.pdf": [_yearly({2013: 5, 2015: 2_000_000})]})
    assert out["status"] == "pass"
    assert [(r["vintage"], r["ratio"]) for r in out["details"]["vintages"]] == [(2013, 1.0), (2014, 0.9)]


def test_issuance_above_monitored_in_a_fully_covered_year_is_flagged(monkeypatch, project):
    _flows(monkeypatch, {2013: 1_300_000, 2014: 500_000})
    p = _with_reports(project, "2012-08-08/2014-08-07")
    out = run.issuance_vs_monitored(p, {"mr0.pdf": [_yearly({2013: 1_000_000, 2014: 600_000})]})
    assert out["status"] == "flag" and "2013" in out["summary"]


def test_issuance_above_monitored_in_a_partly_covered_year_is_info(monkeypatch, project):
    _flows(monkeypatch, {2017: 900_000, 2018: 1_300_000})
    p = _with_reports(project, "2016-08-08/2018-08-07")
    out = run.issuance_vs_monitored(p, {"mr0.pdf": [_yearly({2017: 1_000_000, 2018: 1_000_000})]})
    assert out["status"] == "info" and "only in part" in out["summary"]


def test_monitoring_report_without_period_is_skipped(monkeypatch, project):
    _flows(monkeypatch, {2013: 1_000_000})
    p = _with_reports(project, None)
    out = run.issuance_vs_monitored(p, {"mr0.pdf": [_yearly({2013: 1_000_000, 2014: 1_000_000})]})
    assert out["status"] == "not_available" and "no monitoring period" in out["summary"]
