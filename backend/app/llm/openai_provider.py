from __future__ import annotations

import os

import httpx

from app.llm.base import BaseLLMProvider, HealthCheckResult


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str | None, model: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")

    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        return await self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

    async def repair_json(self, invalid_text: str, error: str) -> str:
        return await self._chat(
            [
                {
                    "role": "system",
                    "content": "Return only valid JSON matching the requested schema. Do not add markdown.",
                },
                {
                    "role": "user",
                    "content": f"Parser error: {error}\nInvalid output:\n{invalid_text}",
                },
            ]
        )

    async def health_check(self) -> HealthCheckResult:
        if not self.api_key:
            return HealthCheckResult(ok=False, reason="API key is not configured")
        try:
            async with self._client(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
        except httpx.TimeoutException:
            return HealthCheckResult(ok=False, reason="Provider request timed out")
        except httpx.HTTPError as exc:
            return HealthCheckResult(ok=False, reason=f"Provider unreachable: {type(exc).__name__}")
        if response.status_code == 200:
            return HealthCheckResult(ok=True, reason="Provider reachable")
        if response.status_code in (401, 403):
            return HealthCheckResult(ok=False, reason="Provider rejected the API key")
        return HealthCheckResult(ok=False, reason=f"Provider returned HTTP {response.status_code}")

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout)

    async def _chat(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("OpenAI API key is not configured")
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": messages, "temperature": 0.1},
            )
            response.raise_for_status()
            payload = response.json()
        return payload["choices"][0]["message"]["content"]

