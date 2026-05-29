from __future__ import annotations

import asyncio

import httpx
import pytest

from app.llm.openai_provider import OpenAIProvider


class _PatchedProvider(OpenAIProvider):
    """OpenAIProvider that uses a caller-supplied httpx transport for tests."""

    def __init__(self, api_key, transport, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self._transport = transport

    def _get_http(self, timeout=None) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            self._http = httpx.AsyncClient(
                transport=self._transport,
                base_url=self.base_url,
                timeout=timeout or self.request_timeout,
                headers=headers,
            )
        return self._http


def test_health_check_ok_when_models_endpoint_returns_200():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"data": []}))
    provider = _PatchedProvider(api_key="sk-test", transport=transport)

    result = asyncio.run(provider.health_check())

    assert result.ok is True
    assert "reachable" in result.reason.lower()


def test_health_check_reports_invalid_key_on_401():
    transport = httpx.MockTransport(lambda request: httpx.Response(401, json={"error": "bad key"}))
    provider = _PatchedProvider(api_key="sk-bad", transport=transport)

    result = asyncio.run(provider.health_check())

    assert result.ok is False
    assert "key" in result.reason.lower()
    assert "sk-bad" not in result.reason


def test_health_check_reports_unreachable_when_network_fails():
    def raise_connect_error(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    transport = httpx.MockTransport(raise_connect_error)
    provider = _PatchedProvider(api_key="sk-test", transport=transport)

    result = asyncio.run(provider.health_check())

    assert result.ok is False
    assert "unreachable" in result.reason.lower()


def test_health_check_without_api_key_does_not_call_network():
    def fail_if_called(_request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("network must not be called when api key is missing")

    transport = httpx.MockTransport(fail_if_called)
    provider = _PatchedProvider(api_key=None, transport=transport)

    result = asyncio.run(provider.health_check())

    assert result.ok is False
    assert "not configured" in result.reason.lower()


_VALID_CHAT_PAYLOAD = {
    "choices": [{"message": {"content": '{"summary":"ok","findings":[]}'}}]
}


def test_chat_retries_on_transient_5xx_and_eventually_succeeds():
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json=_VALID_CHAT_PAYLOAD)

    transport = httpx.MockTransport(handler)
    provider = _PatchedProvider(api_key="sk-test", transport=transport, retry_backoff=0.0)

    content = asyncio.run(provider.analyze("sys", "user"))

    assert content == '{"summary":"ok","findings":[]}'
    assert attempts["count"] == 3


def test_chat_does_not_retry_on_4xx_authentication_error():
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(401, json={"error": "bad key"})

    transport = httpx.MockTransport(handler)
    provider = _PatchedProvider(api_key="sk-bad", transport=transport, retry_backoff=0.0)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(provider.analyze("sys", "user"))
    assert attempts["count"] == 1


def test_chat_retries_on_network_errors_until_giving_up():
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        raise httpx.ConnectError("nope")

    transport = httpx.MockTransport(handler)
    provider = _PatchedProvider(
        api_key="sk-test", transport=transport, max_attempts=3, retry_backoff=0.0
    )

    with pytest.raises(httpx.ConnectError):
        asyncio.run(provider.analyze("sys", "user"))
    assert attempts["count"] == 3


def test_chat_raises_status_error_when_transient_5xx_persists_to_last_attempt():
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(503, json={"error": "still busy"})

    transport = httpx.MockTransport(handler)
    provider = _PatchedProvider(
        api_key="sk-test", transport=transport, max_attempts=3, retry_backoff=0.0
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        asyncio.run(provider.analyze("sys", "user"))
    assert exc_info.value.response.status_code == 503
    assert attempts["count"] == 3


def test_chat_retries_on_429_rate_limit():
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 2:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json=_VALID_CHAT_PAYLOAD)

    transport = httpx.MockTransport(handler)
    provider = _PatchedProvider(api_key="sk-test", transport=transport, retry_backoff=0.0)

    content = asyncio.run(provider.analyze("sys", "user"))

    assert content == '{"summary":"ok","findings":[]}'
    assert attempts["count"] == 2
