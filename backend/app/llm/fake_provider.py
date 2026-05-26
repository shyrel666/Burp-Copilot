from __future__ import annotations

from app.llm.base import BaseLLMProvider, HealthCheckResult


VALID_RESPONSE = (
    '{"summary":"No high-risk issue was identified in the supplied redacted traffic.",'
    '"findings":[{"title":"Traffic accepted for review","severity":"info","confidence":0.2,'
    '"evidence":"The request was redacted and analyzed locally before provider submission.",'
    '"attack_approach":"Use this as a starting point for authorized manual review.",'
    '"remediation":"Review server-side validation and access controls for this endpoint.",'
    '"owasp_category":null}]}'
)


class FakeLLMProvider(BaseLLMProvider):
    def __init__(self, invalid_once: bool = False):
        self.invalid_once = invalid_once
        self.calls = 0

    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        if self.invalid_once and self.calls == 1:
            return "This is not JSON"
        return VALID_RESPONSE

    async def repair_json(self, invalid_text: str, error: str) -> str:
        return VALID_RESPONSE

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(ok=True, reason="Fake provider is always healthy")

