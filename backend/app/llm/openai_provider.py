from __future__ import annotations

import asyncio
import os

import httpx

from app.llm.base import BaseLLMProvider, HealthCheckResult


_TRANSIENT_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


class OpenAIProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str | None,
        model: str | None = None,
        base_url: str | None = None,
        *,
        max_attempts: int = 3,
        request_timeout: float = 20.0,
        retry_backoff: float = 0.5,
    ):
        self.api_key = api_key
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.max_attempts = max_attempts
        self.request_timeout = request_timeout
        self.retry_backoff = retry_backoff

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
        for attempt in range(1, self.max_attempts + 1):
            is_last = attempt == self.max_attempts
            try:
                async with self._client(timeout=self.request_timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"model": self.model, "messages": messages, "temperature": 0.1},
                    )
            except (httpx.TimeoutException, httpx.TransportError):
                if is_last:
                    raise
                await asyncio.sleep(self.retry_backoff * attempt)
                continue

            if response.status_code in _TRANSIENT_STATUS_CODES and not is_last:
                await asyncio.sleep(self.retry_backoff * attempt)
                continue

            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]

        raise AssertionError("unreachable: _chat retry loop must return or raise")

