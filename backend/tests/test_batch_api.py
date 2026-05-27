import json
import time

from fastapi.testclient import TestClient

from app.main import create_app


def test_batch_submit_returns_queued_tasks(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.post(
        "/api/v1/batch/submit",
        json={
            "items": [
                {
                    "source": "dashboard",
                    "mode": "analyze",
                    "request_text": "GET /api/users HTTP/1.1\r\nHost: example.test\r\n\r\n",
                    "target_url": "https://example.test/api/users",
                },
                {
                    "source": "dashboard",
                    "mode": "learn",
                    "request_text": "POST /login HTTP/1.1\r\nHost: example.test\r\n\r\nbody",
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["tasks"]) == 2
    assert body["tasks"][0]["status"] == "queued"
    assert body["tasks"][1]["status"] == "queued"
    assert body["tasks"][0]["task_id"] != body["tasks"][1]["task_id"]


def test_batch_submit_redacts_before_storing(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.post(
        "/api/v1/batch/submit",
        json={
            "items": [
                {
                    "source": "dashboard",
                    "mode": "analyze",
                    "request_text": (
                        "POST /login HTTP/1.1\r\n"
                        "Host: example.test\r\n"
                        "Authorization: Bearer super-secret-token\r\n\r\n"
                        "password=super-secret-pass"
                    ),
                    "target_url": "https://example.test/login?token=secret-url-token",
                }
            ]
        },
    )

    assert response.status_code == 200
    task_id = response.json()["tasks"][0]["task_id"]

    # Verify the stored task data is redacted by checking the DB directly
    import sqlite3
    db_path = tmp_path / "analysis.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM task_queue WHERE task_id = ?", (task_id,)
        ).fetchone()

    assert "super-secret-token" not in row["redacted_request"]
    assert "super-secret-pass" not in row["redacted_request"]
    assert "[REDACTED]" in row["redacted_request"]
    assert "secret-url-token" not in (row["target_url"] or "")


def test_batch_submit_validates_empty_items(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.post("/api/v1/batch/submit", json={"items": []})
    assert response.status_code == 422


def test_batch_submit_validates_max_items(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    items = [
        {"mode": "analyze", "request_text": f"GET /{i} HTTP/1.1\r\nHost: test\r\n\r\n"}
        for i in range(21)
    ]
    response = client.post("/api/v1/batch/submit", json={"items": items})
    assert response.status_code == 422


def test_list_tasks_returns_submitted_tasks(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    client.post(
        "/api/v1/batch/submit",
        json={
            "items": [
                {"mode": "analyze", "request_text": "GET / HTTP/1.1\r\nHost: test\r\n\r\n"}
            ]
        },
    )

    response = client.get("/api/v1/batch/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 1
    assert tasks[0]["status"] in ("queued", "running", "done")


def test_list_tasks_with_status_filter(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    client.post(
        "/api/v1/batch/submit",
        json={
            "items": [
                {"mode": "analyze", "request_text": "GET / HTTP/1.1\r\nHost: test\r\n\r\n"}
            ]
        },
    )

    response = client.get("/api/v1/batch/tasks", params={"status": "queued"})
    assert response.status_code == 200


def test_get_task_by_id(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    submit = client.post(
        "/api/v1/batch/submit",
        json={
            "items": [
                {"mode": "analyze", "request_text": "GET / HTTP/1.1\r\nHost: test\r\n\r\n"}
            ]
        },
    )
    task_id = submit.json()["tasks"][0]["task_id"]

    response = client.get(f"/api/v1/batch/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["task_id"] == task_id


def test_get_task_not_found(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.get("/api/v1/batch/tasks/nonexistent-id")
    assert response.status_code == 404


def test_cancel_queued_task(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    submit = client.post(
        "/api/v1/batch/submit",
        json={
            "items": [
                {"mode": "analyze", "request_text": "GET / HTTP/1.1\r\nHost: test\r\n\r\n"}
            ]
        },
    )
    task_id = submit.json()["tasks"][0]["task_id"]

    response = client.post(f"/api/v1/batch/tasks/{task_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    task = client.get(f"/api/v1/batch/tasks/{task_id}").json()
    assert task["status"] == "cancelled"


def test_cancel_nonexistent_task(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.post("/api/v1/batch/tasks/nonexistent-id/cancel")
    assert response.status_code == 404


def test_cancel_already_cancelled_task(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    submit = client.post(
        "/api/v1/batch/submit",
        json={
            "items": [
                {"mode": "analyze", "request_text": "GET / HTTP/1.1\r\nHost: test\r\n\r\n"}
            ]
        },
    )
    task_id = submit.json()["tasks"][0]["task_id"]

    client.post(f"/api/v1/batch/tasks/{task_id}/cancel")
    response = client.post(f"/api/v1/batch/tasks/{task_id}/cancel")
    assert response.status_code == 409


def test_batch_token_required_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKEND_TOKEN", "test-token")
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    response = client.post(
        "/api/v1/batch/submit",
        json={
            "items": [
                {"mode": "analyze", "request_text": "GET / HTTP/1.1\r\nHost: test\r\n\r\n"}
            ]
        },
    )
    assert response.status_code == 401

    response = client.post(
        "/api/v1/batch/submit",
        headers={"X-Backend-Token": "test-token"},
        json={
            "items": [
                {"mode": "analyze", "request_text": "GET / HTTP/1.1\r\nHost: test\r\n\r\n"}
            ]
        },
    )
    assert response.status_code == 200
