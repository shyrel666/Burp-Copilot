from __future__ import annotations

import asyncio

import httpx

from app.llm.openai_provider import OpenAIProvider


class _PatchedProvider(OpenAIProvider):
    """OpenAIProvider that uses a caller-supplied httpx transport for tests."""

    def __init__(self, api_key, transport, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport, timeout=timeout)


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
