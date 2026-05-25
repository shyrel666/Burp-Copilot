from fastapi.testclient import TestClient

from app.llm.base import HealthCheckResult
from app.main import create_app
from app.llm.fake_provider import VALID_RESPONSE


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
    monkeypatch.setattr("app.main.OpenAIProvider", KeyAwareFakeProvider)
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
