from fastapi.testclient import TestClient

from app.main import create_app


def _submit_analysis(client, mode="analyze", target_url=None):
    payload = {
        "source": "dashboard",
        "mode": mode,
        "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
        "metadata": {"content_encoding": "utf-8"},
    }
    if target_url:
        payload["target_url"] = target_url
    return client.post("/api/v1/analyze", json=payload)


def test_filter_by_mode(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    _submit_analysis(client, mode="analyze")
    _submit_analysis(client, mode="learn")
    _submit_analysis(client, mode="analyze")

    all_items = client.get("/api/v1/history").json()
    assert len(all_items) == 3

    analyze_only = client.get("/api/v1/history", params={"mode": "analyze"}).json()
    assert len(analyze_only) == 2
    assert all(item["mode"] == "analyze" for item in analyze_only)

    learn_only = client.get("/api/v1/history", params={"mode": "learn"}).json()
    assert len(learn_only) == 1
    assert learn_only[0]["mode"] == "learn"


def test_filter_by_target_host(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    _submit_analysis(client, target_url="https://api.example.test/users")
    _submit_analysis(client, target_url="https://admin.example.test/panel")
    _submit_analysis(client, target_url="https://api.example.test/orders")

    api_items = client.get("/api/v1/history", params={"target_host": "api.example.test"}).json()
    assert len(api_items) == 2
    assert all("api.example.test" in item["target_url"] for item in api_items)

    admin_items = client.get("/api/v1/history", params={"target_host": "admin.example.test"}).json()
    assert len(admin_items) == 1


def test_pagination_limit_and_offset(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    for _ in range(5):
        _submit_analysis(client)

    page1 = client.get("/api/v1/history", params={"limit": 2, "offset": 0}).json()
    assert len(page1) == 2

    page2 = client.get("/api/v1/history", params={"limit": 2, "offset": 2}).json()
    assert len(page2) == 2

    page3 = client.get("/api/v1/history", params={"limit": 2, "offset": 4}).json()
    assert len(page3) == 1


def test_filter_by_time_range(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    _submit_analysis(client)
    _submit_analysis(client)

    all_items = client.get("/api/v1/history").json()
    assert len(all_items) == 2

    # Use a far-future 'since' to get nothing
    future = client.get("/api/v1/history", params={"since": "2099-01-01T00:00:00"}).json()
    assert len(future) == 0

    # Use a far-past 'since' to get everything
    past = client.get("/api/v1/history", params={"since": "2000-01-01T00:00:00"}).json()
    assert len(past) == 2


def test_combined_filters(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    _submit_analysis(client, mode="analyze", target_url="https://api.test/a")
    _submit_analysis(client, mode="learn", target_url="https://api.test/b")
    _submit_analysis(client, mode="analyze", target_url="https://other.test/c")

    result = client.get(
        "/api/v1/history",
        params={"mode": "analyze", "target_host": "api.test"},
    ).json()
    assert len(result) == 1
    assert result[0]["mode"] == "analyze"
    assert "api.test" in result[0]["target_url"]


def test_invalid_limit_rejected(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.get("/api/v1/history", params={"limit": 0})
    assert response.status_code == 422

    response = client.get("/api/v1/history", params={"limit": 501})
    assert response.status_code == 422
