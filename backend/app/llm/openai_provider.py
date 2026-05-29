from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator

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
        request_timeout: float = 120.0,
        retry_backoff: float = 0.5,
    ):
        self.api_key = api_key
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.max_attempts = max_attempts
        self.request_timeout = request_timeout
        self.retry_backoff = retry_backoff
        self._http: httpx.AsyncClient | None = None

    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        return await self._chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

    async def analyze_stream(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        async for chunk in self._chat_stream(messages):
            yield chunk

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
            client = self._get_http(timeout=10.0)
            response = await client.get("/models")
        except httpx.TimeoutException:
            return HealthCheckResult(ok=False, reason="Provider request timed out")
        except httpx.HTTPError as exc:
            return HealthCheckResult(ok=False, reason=f"Provider unreachable: {type(exc).__name__}")
        if response.status_code == 200:
            return HealthCheckResult(ok=True, reason="Provider reachable")
        if response.status_code in (401, 403):
            return HealthCheckResult(ok=False, reason="Provider rejected the API key")
        return HealthCheckResult(ok=False, reason=f"Provider returned HTTP {response.status_code}")

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    def _get_http(self, timeout: float | None = None) -> httpx.AsyncClient:
        """Return the shared client, creating it lazily on first use."""
        if self._http is None or self._http.is_closed:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout or self.request_timeout,
                headers=headers,
            )
        return self._http

    async def _chat(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("OpenAI API key is not configured")
        client = self._get_http()
        for attempt in range(1, self.max_attempts + 1):
            is_last = attempt == self.max_attempts
            try:
                response = await client.post(
                    "/chat/completions",
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

    async def _chat_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        if not self.api_key:
            raise RuntimeError("OpenAI API key is not configured")
        client = self._get_http()
        for attempt in range(1, self.max_attempts + 1):
            is_last = attempt == self.max_attempts
            try:
                async with client.stream(
                    "POST",
                    "/chat/completions",
                    json={"model": self.model, "messages": messages, "temperature": 0.1, "stream": True},
                ) as response:
                    if response.status_code in _TRANSIENT_STATUS_CODES and not is_last:
                        await asyncio.sleep(self.retry_backoff * attempt)
                        continue
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[len("data: "):]
                        if data.strip() == "[DONE]":
                            return
                        try:
                            payload = json.loads(data)
                            content = payload.get("choices", [{}])[0].get("delta", {}).get("content")
                            if content:
                                yield content
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
                    return
            except (httpx.TimeoutException, httpx.TransportError):
                if is_last:
                    raise
                await asyncio.sleep(self.retry_backoff * attempt)
                continue

