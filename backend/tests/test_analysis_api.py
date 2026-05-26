import json

from fastapi.testclient import TestClient

from app.llm.base import HealthCheckResult
from app.llm.fake_provider import VALID_RESPONSE
from app.main import create_app


class KeyAwareFakeProvider:
    def __init__(self, api_key=None, model=None, base_url=None):
        self.api_key = api_key

    async def analyze(self, system_prompt, user_prompt):
        if not self.api_key:
            raise RuntimeError("missing api key")
        return VALID_RESPONSE

    async def repair_json(self, invalid_text, error):
        if not self.api_key:
            raise RuntimeError("missing api key")
        return VALID_RESPONSE

    async def health_check(self):
        ok = bool(self.api_key)
        return HealthCheckResult(ok=ok, reason="ok" if ok else "API key is not configured")


def test_analyze_redacts_before_persisting_and_returns_structured_result(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.post(
        "/api/v1/analyze",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "target_url": "https://example.test/login",
            "request_text": (
                "POST /login HTTP/1.1\r\n"
                "Host: example.test\r\n"
                "Authorization: Bearer should-not-persist\r\n"
                "Cookie: session=should-not-persist\r\n\r\n"
                "password=should-not-persist"
            ),
            "response_text": "HTTP/1.1 200 OK\r\nSet-Cookie: sid=should-not-persist\r\n\r\nok",
            "metadata": {"content_encoding": "utf-8"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["redaction_applied"] is True
    assert body["llm_status"] == "ok"
    assert body["findings"][0]["severity"] == "info"

    history = client.get("/api/v1/history").json()
    serialized = str(history)
    assert "should-not-persist" not in serialized
    assert "[REDACTED]" in serialized


def test_settings_endpoint_never_returns_plain_api_key(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.put(
        "/api/v1/settings/provider",
        json={"provider": "openai", "model": "gpt-test", "api_key": "sk-test-key-9999"},
    )
    assert response.status_code == 200

    settings = client.get("/api/v1/settings").json()
    assert settings["masked_api_key"] == "sk-...9999"
    assert "sk-test-key-9999" not in str(settings)


def test_invalid_llm_json_is_repaired_once(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake-invalid-once")
    client = TestClient(app)

    response = client.post(
        "/api/v1/analyze",
        json={
            "source": "dashboard",
            "mode": "learn",
            "request_text": "GET /profile HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    )

    assert response.status_code == 200
    assert response.json()["llm_status"] == "repaired"


def test_local_dashboard_origin_is_allowed_for_cors(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.options(
        "/api/v1/analyze",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_any_localhost_port_is_allowed_for_cors(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    for origin in ("http://localhost:5174", "http://127.0.0.1:3001", "http://localhost"):
        response = client.options(
            "/api/v1/analyze",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_external_origin_is_rejected_for_cors(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.options(
        "/api/v1/analyze",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_backend_token_is_required_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKEND_TOKEN", "unit-test-token")
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)
    payload = {
        "source": "dashboard",
        "mode": "analyze",
        "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
        "metadata": {"content_encoding": "utf-8"},
    }

    assert client.get("/api/v1/health").status_code == 200
    assert client.post("/api/v1/analyze", json=payload).status_code == 401
    assert client.post("/api/v1/analyze", headers={"X-Backend-Token": "wrong"}, json=payload).status_code == 401
    assert (
        client.post("/api/v1/analyze", headers={"X-Backend-Token": "unit-test-token"}, json=payload).status_code
        == 200
    )
    assert client.get("/api/v1/settings", headers={"X-Backend-Token": "wrong"}).status_code == 401


def test_provider_settings_update_is_used_without_restart(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("app.llm.provider_registry.OpenAIProvider", KeyAwareFakeProvider)
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    update = client.put(
        "/api/v1/settings/provider",
        json={"provider": "openai", "model": "gpt-test", "api_key": "sk-test-key-2222"},
    )
    assert update.status_code == 200

    response = client.post(
        "/api/v1/analyze",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    )

    assert response.status_code == 200
    assert response.json()["llm_status"] == "ok"


class FailingProvider:
    """Provider that always raises a network-style error to simulate outages."""

    def __init__(self, api_key=None, model=None, base_url=None):
        pass

    async def analyze(self, system_prompt, user_prompt):
        raise RuntimeError("simulated upstream outage")

    async def repair_json(self, invalid_text, error):
        raise RuntimeError("simulated upstream outage")

    async def health_check(self):
        return HealthCheckResult(ok=False, reason="simulated outage")


def test_provider_outage_returns_failed_status_and_does_not_leak_secrets(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("app.main.build_provider", lambda config: FailingProvider())
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    sensitive_request = (
        "POST /login HTTP/1.1\r\n"
        "Host: example.test\r\n"
        "Authorization: Bearer ultra-secret-token-2222\r\n\r\n"
        "password=ultra-secret-token-2222"
    )

    with caplog.at_level("WARNING"):
        response = client.post(
            "/api/v1/analyze",
            json={
                "source": "dashboard",
                "mode": "analyze",
                "request_text": sensitive_request,
                "metadata": {"content_encoding": "utf-8"},
            },
        )

    assert response.status_code == 200
    assert response.json()["llm_status"] == "failed"
    assert "ultra-secret-token-2222" not in caplog.text

    history_response = client.get("/api/v1/history").json()
    assert "ultra-secret-token-2222" not in str(history_response)
    assert history_response[0]["llm_status"] == "failed"


def test_test_provider_endpoint_returns_structured_reason(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("app.llm.provider_registry.OpenAIProvider", KeyAwareFakeProvider)
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    before = client.post("/api/v1/settings/test-provider").json()
    assert before["ok"] is False
    assert "configured" in before["reason"]

    saved = client.put(
        "/api/v1/settings/provider",
        json={"provider": "openai", "model": "gpt-test", "api_key": "sk-test-key-3333"},
    )
    assert saved.status_code == 200

    after = client.post("/api/v1/settings/test-provider").json()
    assert after["ok"] is True
    assert "sk-test-key-3333" not in str(after)


class BrokenJsonProvider:
    async def analyze(self, system_prompt, user_prompt):
        return "not json"

    async def repair_json(self, invalid_text, error):
        return "still not json"

    async def health_check(self):
        return HealthCheckResult(ok=True, reason="ok")


class CapturingProvider:
    def __init__(self):
        self.calls = []

    async def analyze(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return VALID_RESPONSE

    async def repair_json(self, invalid_text, error):
        return VALID_RESPONSE

    async def health_check(self):
        return HealthCheckResult(ok=True, reason="ok")



def test_target_url_query_secrets_are_redacted_before_provider_and_history(tmp_path, monkeypatch):
    provider = CapturingProvider()
    monkeypatch.setattr("app.main.build_provider", lambda config: provider)
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/analyze",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "target_url": "https://example.test/callback?code=super-code-123&token=super-token-456&view=profile",
            "request_text": "GET /callback HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    )

    assert response.status_code == 200
    prompt = provider.calls[-1][1]
    assert "super-code-123" not in prompt
    assert "super-token-456" not in prompt
    assert "code=[REDACTED]" in prompt
    assert "token=[REDACTED]" in prompt
    assert "view=profile" in prompt
    history = client.get("/api/v1/history").json()
    assert "super-code-123" not in str(history)
    assert "super-token-456" not in str(history)
    assert history[0]["target_url"] == "https://example.test/callback?code=[REDACTED]&token=[REDACTED]&view=profile"


def test_saved_provider_model_and_base_url_are_used_without_restart(tmp_path, monkeypatch):
    seen = []
    provider = CapturingProvider()

    def fake_build_provider(config):
        seen.append(config)
        return provider

    monkeypatch.setattr("app.main.build_provider", fake_build_provider)
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    saved = client.put(
        "/api/v1/settings/provider",
        json={
            "provider": "openai-compatible",
            "model": "gpt-compat",
            "api_key": "sk-test-key-4444",
            "base_url": "http://127.0.0.1:11434/v1",
        },
    )
    assert saved.status_code == 200

    response = client.post(
        "/api/v1/analyze",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    )

    assert response.status_code == 200
    assert response.json()["llm_status"] == "ok"
    assert seen[-1].provider == "openai-compatible"
    assert seen[-1].model == "gpt-compat"
    assert seen[-1].base_url == "http://127.0.0.1:11434/v1"


def test_invalid_provider_output_returns_failed_status_when_repair_also_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.build_provider", lambda config: BrokenJsonProvider())
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/analyze",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    )

    assert response.status_code == 200
    assert response.json()["llm_status"] == "failed"
    history = client.get("/api/v1/history").json()
    assert history[0]["llm_status"] == "failed"


class SchemaViolatingRepairProvider:
    async def analyze(self, system_prompt, user_prompt):
        return "not json"

    async def repair_json(self, invalid_text, error):
        return '{"summary":"repaired but bad","findings":[{"title":"missing fields"}]}'

    async def health_check(self):
        return HealthCheckResult(ok=True, reason="ok")


def test_repair_returning_valid_json_but_invalid_schema_still_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.build_provider", lambda config: SchemaViolatingRepairProvider())
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/analyze",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    )

    assert response.status_code == 200
    assert response.json()["llm_status"] == "failed"
    history = client.get("/api/v1/history").json()
    assert history[0]["llm_status"] == "failed"


def test_stream_analyze_emits_progress_result_and_no_raw_secrets(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)
    secret = "stream-secret-7777"

    with client.stream(
        "POST",
        "/api/v1/analyze/stream",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "request_text": (
                "POST /login HTTP/1.1\r\n"
                "Host: example.test\r\n"
                f"Authorization: Bearer {secret}\r\n\r\n"
                f"password={secret}"
            ),
            "metadata": {"content_encoding": "utf-8"},
        },
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = response.read().decode("utf-8")

    events = _decode_sse(body)
    statuses = [data["status"] for event, data in events if event == "status"]
    result = [data["analysis"] for event, data in events if event == "result"][0]

    assert statuses == ["redacting", "calling_provider", "parsing", "persisted"]
    assert result["llm_status"] == "ok"
    assert secret not in body
    assert client.get("/api/v1/history").json()[0]["llm_status"] == "ok"


def test_stream_analyze_emits_failed_status_for_unusable_provider_output(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.build_provider", lambda config: BrokenJsonProvider())
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/v1/analyze/stream",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    ) as response:
        assert response.status_code == 200
        body = response.read().decode("utf-8")

    events = _decode_sse(body)
    statuses = [data["status"] for event, data in events if event == "status"]
    result = [data["analysis"] for event, data in events if event == "result"][0]

    assert statuses[-1] == "failed"
    assert result["llm_status"] == "failed"
    assert client.get("/api/v1/history").json()[0]["llm_status"] == "failed"



def test_stream_provider_exception_skips_parsing_status(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.build_provider", lambda config: FailingProvider())
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/v1/analyze/stream",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    ) as response:
        assert response.status_code == 200
        body = response.read().decode("utf-8")

    events = _decode_sse(body)
    statuses = [data["status"] for event, data in events if event == "status"]

    assert statuses == ["redacting", "calling_provider", "failed"]


def test_stream_target_url_secrets_are_redacted(tmp_path, monkeypatch):
    provider = CapturingProvider()
    monkeypatch.setattr("app.main.build_provider", lambda config: provider)
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/v1/analyze/stream",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "target_url": "https://example.test/auth?code=secret-code&token=secret-token&page=1",
            "request_text": "GET /auth HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    ) as response:
        assert response.status_code == 200
        body = response.read().decode("utf-8")

    events = _decode_sse(body)
    result = [data["analysis"] for event, data in events if event == "result"][0]
    assert result["llm_status"] == "ok"

    prompt = provider.calls[-1][1]
    assert "secret-code" not in prompt
    assert "secret-token" not in prompt
    assert "code=[REDACTED]" in prompt
    assert "token=[REDACTED]" in prompt
    assert "page=1" in prompt

    history = client.get("/api/v1/history").json()
    assert "secret-code" not in str(history)
    assert "secret-token" not in str(history)
    assert history[0]["target_url"] == "https://example.test/auth?code=[REDACTED]&token=[REDACTED]&page=1"


def test_provider_outage_with_sensitive_url_does_not_leak_to_history(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("app.main.build_provider", lambda config: FailingProvider())
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    with caplog.at_level("WARNING"):
        response = client.post(
            "/api/v1/analyze",
            json={
                "source": "dashboard",
                "mode": "analyze",
                "target_url": "https://example.test/login?token=super-secret-token&session=abc123",
                "request_text": "GET /login HTTP/1.1\r\nHost: example.test\r\n\r\n",
                "metadata": {"content_encoding": "utf-8"},
            },
        )

    assert response.status_code == 200
    assert response.json()["llm_status"] == "failed"
    assert "super-secret-token" not in caplog.text

    history_response = client.get("/api/v1/history").json()
    assert "super-secret-token" not in str(history_response)
    assert "abc123" not in str(history_response)
    assert history_response[0]["target_url"] == "https://example.test/login?token=[REDACTED]&session=[REDACTED]"
    assert history_response[0]["llm_status"] == "failed"


def _decode_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        event_name = ""
        data_lines = []
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            if line.startswith("data: "):
                data_lines.append(line.removeprefix("data: "))
        if event_name and data_lines:
            events.append((event_name, json.loads("\n".join(data_lines))))
    return events
