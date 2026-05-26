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


_VALID_JSON = (
    '{"summary":"Checked","findings":[{"title":"Info leak","severity":"low",'
    '"confidence":0.4,"evidence":"server header","attack_approach":"Review.",'
    '"remediation":"Remove version headers."}]}'
)


def test_parse_strips_markdown_code_fence_with_json_tag():
    parsed = parse_llm_json(f"```json\n{_VALID_JSON}\n```")

    assert parsed["summary"] == "Checked"


def test_parse_strips_markdown_code_fence_without_language_tag():
    parsed = parse_llm_json(f"```\n{_VALID_JSON}\n```")

    assert parsed["summary"] == "Checked"


def test_parse_handles_chatty_prefix_and_suffix():
    chatty = f"Sure, here is the result:\n{_VALID_JSON}\nLet me know if you need more."

    parsed = parse_llm_json(chatty)

    assert parsed["findings"][0]["severity"] == "low"


def test_parse_keeps_nested_objects_inside_fenced_block():
    nested = (
        '{"summary":"Nested","findings":[{"title":"x","severity":"info","confidence":0.1,'
        '"evidence":"e","attack_approach":"a","remediation":"r","owasp_category":null,'
        '"extra":{"meta":{"key":"value"}}}]}'
    )

    parsed = parse_llm_json(f"```json\n{nested}\n```")

    assert parsed["findings"][0]["extra"]["meta"]["key"] == "value"


def test_parse_prefers_json_containing_fence_over_first_block():
    text = '```\nSome other code\n```\n```json\n{"summary":"ok","findings":[{"title":"x","severity":"info","confidence":0.1,"evidence":"e","attack_approach":"a","remediation":"r"}]}\n```'
    parsed = parse_llm_json(text)
    assert parsed["summary"] == "ok"


def test_parse_extracts_balanced_json_ignoring_trailing_braces():
    text = '{"summary":"ok","findings":[{"title":"x","severity":"info","confidence":0.1,"evidence":"e","attack_approach":"a","remediation":"r"}]} } thank you'
    parsed = parse_llm_json(text)
    assert parsed["summary"] == "ok"


def test_parse_rejects_empty_response():
    with pytest.raises(ValueError):
        parse_llm_json("")
    with pytest.raises(ValueError):
        parse_llm_json("   \n  ")
