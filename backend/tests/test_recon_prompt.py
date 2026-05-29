import pytest

from app.llm.result_parser import parse_llm_json
from app.models.schemas import AnalysisMode, Finding, Severity
from app.services.prompt_builder import (
    ANALYZE_SYSTEM_PROMPT,
    LEARN_SYSTEM_PROMPT,
    RECON_SYSTEM_PROMPT,
    build_prompt,
)


def test_recon_mode_uses_recon_system_prompt_and_schema():
    system, user = build_prompt(
        AnalysisMode.RECON,
        "GET /api/users/1 HTTP/1.1\r\nHost: example.test\r\n\r\n",
        "HTTP/1.1 200 OK\r\n\r\n{}",
        "https://example.test/api/users/1",
    )

    assert system == RECON_SYSTEM_PROMPT
    assert "verification_steps" in user
    assert "priority" in user


def test_analyze_and_learn_modes_keep_their_prompts():
    analyze_system, _ = build_prompt(AnalysisMode.ANALYZE, "GET / HTTP/1.1\r\n\r\n", None, None)
    learn_system, _ = build_prompt(AnalysisMode.LEARN, "GET / HTTP/1.1\r\n\r\n", None, None)

    assert analyze_system == ANALYZE_SYSTEM_PROMPT
    assert learn_system == LEARN_SYSTEM_PROMPT


def test_parser_accepts_recon_fields():
    parsed = parse_llm_json(
        '{"summary":"recon","findings":[{"title":"疑似越权","severity":"medium",'
        '"priority":1,"confidence":0.55,"evidence":"路径含用户 id","attack_approach":"替换 id 越权",'
        '"remediation":"服务端校验归属","verification_steps":["替换 id","观察是否返回他人数据"],'
        '"owasp_category":"A01:2021 - 失效的访问控制"}]}'
    )

    finding = parsed["findings"][0]
    assert finding["priority"] == 1
    assert finding["verification_steps"] == ["替换 id", "观察是否返回他人数据"]


def test_parser_rejects_priority_out_of_range():
    with pytest.raises(ValueError):
        parse_llm_json(
            '{"summary":"x","findings":[{"title":"t","severity":"low","priority":9,'
            '"confidence":0.5,"evidence":"e","attack_approach":"a","remediation":"r"}]}'
        )


def test_finding_model_defaults_are_backward_compatible():
    finding = Finding.model_validate(
        {
            "title": "legacy",
            "severity": "info",
            "confidence": 0.5,
            "evidence": "e",
            "attack_approach": "a",
            "remediation": "r",
        }
    )

    assert finding.verification_steps == []
    assert finding.priority is None
    assert finding.severity == Severity.INFO
