from core.ai.decision import Decision, DecisionError, parse_decision
from core.ai.methodology import methodology_status
from core.ai.report import overall_score
from core.hashing import canonical_json, hash_json

JEV_RESPONSE = {
    "model": "typesafe/jev-1.13-20260917",
    "answers": {
        "evidence_level": {"type": "choice", "choice": "documentary",
                           "probabilities": {"quantified_verifiable": 0.1, "documentary": 0.7,
                                             "assertion_only": 0.2, "not_addressed": 0.0},
                           "confidence": 0.6},
        "independent": {"type": "noul", "noul": 0.3},
        "strength": {"type": "score", "score": 1.5, "legend": {}, "probabilities": {"1": 0.4, "2": 0.6},
                     "confidence": 0.5},
    },
    "usage": {"input_tokens": 10, "output_tokens": 5},
}


def test_parse_decision_maps_strength_to_0_100():
    d = parse_decision(JEV_RESPONSE)
    assert isinstance(d, Decision)
    assert d.evidence_level == "documentary" and d.score == 50


def test_methodology_lookup():
    assert methodology_status("ACM0002", "19")["status"] == "not_approved"
    assert methodology_status("acm0001", "16")["status"] == "approved_with_conditions"
    assert methodology_status("ACM0001", "12")["status"] == "not_ccp_approved"
    assert methodology_status("VM9999")["status"] == "unknown"
    assert methodology_status("VM0050", "1.0")["status"] == "approved_with_conditions"
    assert methodology_status("VM0010", "1.4")["status"] == "under_assessment"
    assert methodology_status("VM0010", "1.2")["status"] == "not_ccp_approved"  # decision covers v1.4 only


def test_methodology_table_is_sourced():
    from core.ai.methodology import load_table
    table = load_table()
    for entry in table["methodologies"]:
        assert entry["status"] in table["statuses"], entry["code"]
        assert entry["sources"] and all(s.startswith("https://") for s in entry["sources"]), entry["code"]


def test_overall_renormalizes_weights_and_skips_none():
    ps = [{"principle": "additionality", "score": 100},   # weight 0.25
          {"principle": "safeguards", "score": 0},        # weight 0.15
          {"principle": "permanence", "score": None}]
    o = overall_score(ps)
    assert o["score"] == round(100 * 0.25 / 0.40)
    assert o["excluded"] == ["permanence"]


def test_parse_repairs_unescaped_quotes_in_model_json():
    from core.ai.assess import _parse
    raw = ('{"principle": "additionality", "status": "evidence_weak", "score": 30, "rationale": "r", '
           '"quotes": [{"paragraph_id": "p1-01", "text": "the so called "baseline" scenario applies here"}]}')
    f = _parse(raw)
    assert f.quotes[0].text == 'the so called "baseline" scenario applies here'


def test_permanence_rule_for_emission_avoidance():
    from core.ai.report import not_applicable_by_rule
    e = not_applicable_by_rule("permanence")
    assert e["status"] == "not_applicable" and e["score"] is None and e["rule"] == "no_reversal_risk"


def test_canonical_hash_is_key_order_independent():
    assert canonical_json({"b": 1, "a": "ş"}) == '{"a":"ş","b":1}'.encode("utf-8")
    assert hash_json({"a": 1, "b": 2}) == hash_json({"b": 2, "a": 1})
    assert hash_json({}) == "0x" + "b48d38f93eaa084033fc5970bf96e559c33c4cdc07d889ab00b4d63f9590739d"
