from core.ai.pdf_extract import Document, Paragraph
from core.ai.quotes import QuoteVerifier, normalize


def make_doc(*texts: str) -> Document:
    paras = [Paragraph(id=f"p1-{i + 1:02d}", page=1, text=t) for i, t in enumerate(texts)]
    return Document(path="test.pdf", sha256="0" * 64, page_count=1, paragraphs=paras)


DOC = make_doc(
    "Project overview. The project installs solar panels in Rajasthan.",
    "The project is adﬁtional because the equity IRR of 9.1% is below the bench-\nmark of 14.5% for this sector.",
    "Stakeholders were invited to a “public meeting” – held on 12 May 2018 in the village hall.",
    "Non-\npermanence risk is not applicable to grid-connected renewable energy activities.",
    "This paragraph continues the previous sentence and mentions the buffer pool.",
)


def test_normalize_handles_ligatures_hyphenation_and_quotes():
    assert normalize("adﬁtional bench-\nmark “x” –") == 'adfitional benchmark "x" -'


def test_exact_match_in_cited_paragraph():
    check = QuoteVerifier(DOC).check("equity IRR of 9.1% is below the benchmark of 14.5%", "p1-02")
    assert check.verified and check.method == "exact" and check.paragraph_id == "p1-02"


def test_straight_quotes_match_curly_quotes():
    check = QuoteVerifier(DOC).check('invited to a "public meeting" - held on 12 May 2018', "p1-03")
    assert check.verified and check.method == "exact"


def test_quote_found_in_wrong_paragraph_is_relocated():
    check = QuoteVerifier(DOC).check("installs solar panels in Rajasthan", "p1-05")
    assert check.verified and check.method == "exact_relocated" and check.paragraph_id == "p1-01"


def test_neighbouring_paragraph_counts_as_cited():
    quote = "renewable energy activities. This paragraph continues the previous sentence"
    check = QuoteVerifier(DOC).check(quote, "p1-04")
    assert check.verified and check.method == "exact"


def test_alnum_fallback_for_long_quote_with_hyphen_difference():
    quote = "Non-permanence risk is not applicable to grid-connected renewable energy"
    check = QuoteVerifier(DOC).check(quote, "p1-04")
    assert check.verified and check.method == "alnum"


def test_short_quote_rejected():
    assert QuoteVerifier(DOC).check("solar panels", "p1-01").method == "rejected:too_short"


def test_ellipsis_rejected():
    check = QuoteVerifier(DOC).check("The project is adfitional ... for this sector.", "p1-02")
    assert check.method == "rejected:ellipsis"


def test_invented_quote_rejected():
    check = QuoteVerifier(DOC).check("The project received a government subsidy of 40% of capex.", "p1-02")
    assert not check.verified and check.method == "rejected:not_found"
