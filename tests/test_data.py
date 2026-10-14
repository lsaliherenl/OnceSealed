import pandas as pd

from core.data.anonymity import classify
from core.data.batches import load_batches
from core.privacy.identity import text_id


def row(ben=None, harm=None, note=None):
    return {"retirement_beneficiary": ben, "retirement_beneficiary_harmonized": harm, "retirement_note": note}


CASES = [
    (row(ben="Not Disclosed"), "explicitly_undisclosed"),
    (row(ben="not public"), "explicitly_undisclosed"),
    (row(note="Private offset"), "explicitly_undisclosed"),
    (row(note="Gold Standard Marketplace Order GSM31080 for anonymous"), "explicitly_undisclosed"),
    (row(ben="Medibank Private Limited"), "named"),  # "private" inside a company name is not anonymity
    (row(ben="Temasek Holdings (Private) Limited", harm="temasek"), "named"),
    (row(ben="4AIR client"), "intermediary_only"),
    (row(ben="On behalf of Patch's customers and/ or their End Users"), "intermediary_only"),
    (row(harm="Ambify Clients"), "intermediary_only"),
    (row(note="Retired on behalf of DNV Singapore Pte Ltd"), "named_in_note"),
    (row(note="Gold Standard Marketplace Order GSM2337 for Jane Doe"), "named_in_note"),
    (row(note="Environmental benefit"), "generic_note"),
    (row(note="Stand For Trees Retirement, Order #553a353ef3923"), "generic_note"),
    (row(), "no_information"),
    (row(ben="   ", note=""), "no_information"),
]


def test_anonymity_classes():
    df = pd.DataFrame([c[0] for c in CASES])
    got = classify(df).tolist()
    expected = [c[1] for c in CASES]
    mismatches = [(CASES[i][0], g, e) for i, (g, e) in enumerate(zip(got, expected)) if g != e]
    assert not mismatches, mismatches


def test_batches_file_is_consistent():
    batches = load_batches()
    assert len(batches) > 0
    assert len({b.key for b in batches}) == len(batches)
    for b in batches:
        assert b.batch_id == text_id(b.key)
        assert b.first_serial == 1 and b.quantity == b.last_serial
    assert {b.project_id for b in batches} == {"VCS1477", "VCS1851", "VCS138", "VCS2505"}
