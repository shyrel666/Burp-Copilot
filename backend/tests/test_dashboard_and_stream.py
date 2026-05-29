"""Tests for the aggregated dashboard endpoint and the task SSE stream.

The SSE test specifically guards against a regression where `asyncio` was not
imported at module level in app/main.py, which made the
`/api/v1/batch/tasks/stream` generator raise NameError on its first sleep.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_dashboard_endpoint_returns_three_sections(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.get("/api/v1/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"statistics", "recent_findings", "attack_surface"}
    assert body["statistics"]["total_analyses"] == 0
    assert body["recent_findings"] == []
    assert body["attack_surface"]["endpoints"] == []


def test_dashboard_rejects_invalid_since(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.get("/api/v1/dashboard", params={"since": "not-a-date"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_task_stream_yields_frames_without_nameerror(tmp_path):
    """Drive the SSE generator past its first sleep to catch a missing
    module-level `import asyncio` (regression guard)."""
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    with TestClient(app):  # trigger lifespan so the worker exists
        # Find the registered stream route and call its endpoint directly so we
        # can iterate the async generator deterministically.
        endpoint = next(
            route.endpoint
            for route in app.routes
            if getattr(route, "path", None) == "/api/v1/batch/tasks/stream"
        )
        response = await endpoint()
        agen = response.body_iterator

        # First frame is emitted before the first sleep.
        first = await agen.__anext__()
        assert "data:" in (first if isinstance(first, str) else first.decode())

        # The second iteration runs `await asyncio.sleep(...)`. With no task
        # state change the generator stays in that sleep, so wait_for times out
        # on a *healthy* generator. The point of the assertion is that we reach
        # the sleep at all: a missing module-level `import asyncio` would raise
        # NameError here instead of timing out.
        try:
            await asyncio.wait_for(agen.__anext__(), timeout=0.2)
        except asyncio.TimeoutError:
            pass  # expected: generator is alive and sleeping
        finally:
            await agen.aclose()
