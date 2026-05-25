import pytest

from app.llm.result_parser import parse_llm_json


def test_parse_valid_llm_json_response():
    parsed = parse_llm_json(
        '{"summary":"Checked","findings":[{"title":"Info leak","severity":"low","confidence":0.4,'
        '"evidence":"server header","attack_approach":"Review exposed headers in an authorized test.",'
        '"remediation":"Remove version headers.","owasp_category":"A05:2021 - Security Misconfiguration"}]}'
    )

    assert parsed["summary"] == "Checked"
    assert parsed["findings"][0]["severity"] == "low"


def test_rejects_missing_required_finding_fields():
    with pytest.raises(ValueError):
        parse_llm_json('{"summary":"Bad","findings":[{"title":"Missing severity"}]}')
