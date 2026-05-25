from fastapi.testclient import TestClient

from app.main import create_app


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
        json={"provider": "openai", "model": "gpt-test", "api_key": "sk-secret-value-9999"},
    )
    assert response.status_code == 200

    settings = client.get("/api/v1/settings").json()
    assert settings["masked_api_key"] == "sk-...9999"
    assert "sk-secret-value-9999" not in str(settings)


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
