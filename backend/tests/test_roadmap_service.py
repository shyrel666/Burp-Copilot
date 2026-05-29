import asyncio
import json

from app.llm.base import HealthCheckResult
from app.models.schemas import (
    AnalysisMetadata,
    AnalysisMode,
    AnalysisResponse,
    Finding,
    Source,
)
from app.services.fingerprint_service import FingerprintService
from app.services.history_store import HistoryStore
from app.services.roadmap_service import RoadmapService
from app.services.statistics_service import StatisticsService


_ROADMAP_JSON = json.dumps(
    {
        "stages": [
            {
                "stage": "访问控制与越权测试",
                "objective": "验证用户数据接口是否存在 IDOR",
                "steps": [
                    {
                        "target": "GET /api/users/{id}",
                        "suspected_vuln": "IDOR 越权",
                        "reason": "路径含用户 id 且需认证",
                        "verification_steps": ["用低权账号替换 id", "观察是否返回他人数据"],
                        "priority": 1,
                    }
                ],
            }
        ]
    }
)


class RoadmapProvider:
    def __init__(self, output=_ROADMAP_JSON, fail=False, bad_then_repair=False):
        self.output = output
        self.fail = fail
        self.bad_then_repair = bad_then_repair
        self.calls = 0
        self.last_prompt = None

    async def analyze(self, system_prompt, user_prompt):
        self.calls += 1
        self.last_prompt = user_prompt
        if self.fail:
            raise RuntimeError("boom")
        if self.bad_then_repair:
            return "not json"
        return self.output

    async def analyze_stream(self, system_prompt, user_prompt):
        yield await self.analyze(system_prompt, user_prompt)

    async def repair_json(self, invalid_text, error):
        return self.output

    async def health_check(self):
        return HealthCheckResult(ok=True, reason="ok")


def _seed(store, *, host="api.test"):
    analysis = AnalysisResponse(
        analysis_id=store.create_analysis_id(),
        summary="s",
        findings=[
            Finding.model_validate(
                {
                    "title": "疑似越权",
                    "severity": "high",
                    "confidence": 0.6,
                    "evidence": "e",
                    "attack_approach": "a",
                    "remediation": "r",
                    "owasp_category": "A01",
                }
            )
        ],
        redaction_applied=True,
        llm_status="ok",
    )
    store.save(
        source=Source.BURP,
        mode=AnalysisMode.RECON,
        target_url=f"https://{host}/api/users/1",
        request_text=f"GET /api/users/1 HTTP/1.1\r\nHost: {host}\r\nAuthorization: Bearer [REDACTED]\r\n\r\n",
        response_text="HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{}",
        metadata=AnalysisMetadata(),
        analysis=analysis,
    )


def _service(store, provider):
    return RoadmapService(store, FingerprintService(store), StatisticsService(store), provider)


def test_roadmap_builds_stages_and_includes_context_in_prompt(tmp_path):
    store = HistoryStore(tmp_path)
    _seed(store)
    provider = RoadmapProvider()

    result = asyncio.run(_service(store, provider).build("api.test"))

    assert result.llm_status == "ok"
    assert result.stages[0].stage == "访问控制与越权测试"
    assert result.stages[0].steps[0].priority == 1
    assert "rest_api" in result.architecture.system_types
    assert "/api/users/{id}" in provider.last_prompt
    assert "系统类型" in provider.last_prompt


def test_roadmap_empty_host_returns_guidance(tmp_path):
    store = HistoryStore(tmp_path)
    result = asyncio.run(_service(store, RoadmapProvider()).build("nobody.test"))
    assert result.stages == []
    assert result.llm_status == "ok"
    assert "暂无" in (result.notes or "")


def test_roadmap_repairs_invalid_then_succeeds(tmp_path):
    store = HistoryStore(tmp_path)
    _seed(store)
    result = asyncio.run(_service(store, RoadmapProvider(bad_then_repair=True)).build("api.test"))
    assert result.llm_status == "repaired"
    assert len(result.stages) == 1


def test_roadmap_provider_failure_yields_failed_status(tmp_path):
    store = HistoryStore(tmp_path)
    _seed(store)
    result = asyncio.run(_service(store, RoadmapProvider(fail=True)).build("api.test"))
    assert result.llm_status == "failed"
    assert result.stages == []
