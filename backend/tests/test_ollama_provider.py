from __future__ import annotations

import asyncio

import httpx
import pytest

from app.llm.ollama_provider import OllamaProvider


class _PatchedProvider(OllamaProvider):
    """OllamaProvider that uses a caller-supplied httpx transport for tests."""

    def __init__(self, transport, **kwargs):
        super().__init__(**kwargs)
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport, timeout=timeout)


def test_health_check_ok_when_tags_endpoint_returns_200():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"models": []}))
    provider = _PatchedProvider(transport)

    result = asyncio.run(provider.health_check())

    assert result.ok is True
    assert "running" in result.reason.lower()


def test_health_check_reports_unreachable_when_network_fails():
    def raise_connect_error(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    transport = httpx.MockTransport(raise_connect_error)
    provider = _PatchedProvider(transport)

    result = asyncio.run(provider.health_check())

    assert result.ok is False
    assert "unreachable" in result.reason.lower()


def test_health_check_reports_timeout():
    def raise_timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    transport = httpx.MockTransport(raise_timeout)
    provider = _PatchedProvider(transport)

    result = asyncio.run(provider.health_check())

    assert result.ok is False
    assert "timed out" in result.reason.lower()


def test_health_check_reports_non_200_status():
    transport = httpx.MockTransport(lambda request: httpx.Response(500, json={"error": "internal"}))
    provider = _PatchedProvider(transport)

    result = asyncio.run(provider.health_check())

    assert result.ok is False
    assert "500" in result.reason


_VALID_CHAT_PAYLOAD = {
    "choices": [{"message": {"content": '{"summary":"ok","findings":[]}'}}]
}


def test_chat_sends_to_v1_chat_completions_without_auth():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = request.content.decode()
        return httpx.Response(200, json=_VALID_CHAT_PAYLOAD)

    transport = httpx.MockTransport(handler)
    provider = _PatchedProvider(transport, model="llama3")

    content = asyncio.run(provider.analyze("sys", "user"))

    assert content == '{"summary":"ok","findings":[]}'
    assert "/v1/chat/completions" in captured["url"]
    assert "Authorization" not in captured["headers"]


def test_chat_retries_on_transient_5xx_and_eventually_succeeds():
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json=_VALID_CHAT_PAYLOAD)

    transport = httpx.MockTransport(handler)
    provider = _PatchedProvider(transport, retry_backoff=0.0)

    content = asyncio.run(provider.analyze("sys", "user"))

    assert content == '{"summary":"ok","findings":[]}'
    assert attempts["count"] == 3


def test_chat_raises_on_persistent_5xx():
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={"error": "busy"}))
    provider = _PatchedProvider(transport, max_attempts=2, retry_backoff=0.0)

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        asyncio.run(provider.analyze("sys", "user"))
    assert exc_info.value.response.status_code == 503


def test_chat_retries_on_network_error_until_giving_up():
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        raise httpx.ConnectError("nope")

    transport = httpx.MockTransport(handler)
    provider = _PatchedProvider(transport, max_attempts=3, retry_backoff=0.0)

    with pytest.raises(httpx.ConnectError):
        asyncio.run(provider.analyze("sys", "user"))
    assert attempts["count"] == 3


def test_repair_json_sends_messages_and_returns_content():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=_VALID_CHAT_PAYLOAD))
    provider = _PatchedProvider(transport)

    content = asyncio.run(provider.repair_json("bad json", "parse error"))
    assert content == '{"summary":"ok","findings":[]}'


def test_default_timeout_is_longer_than_openai():
    provider = OllamaProvider()
    assert provider.request_timeout == 120.0


def test_default_base_url_is_localhost():
    provider = OllamaProvider()
    assert provider.base_url == "http://localhost:11434"


def test_default_model_is_llama3():
    provider = OllamaProvider()
    assert provider.model == "llama3"


def test_custom_base_url_and_model():
    provider = OllamaProvider(model="mistral", base_url="http://192.168.1.10:11434")
    assert provider.model == "mistral"
    assert provider.base_url == "http://192.168.1.10:11434"
