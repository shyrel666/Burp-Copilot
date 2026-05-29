from app.core.database import Database
from app.models.schemas import (
    AnalysisMetadata,
    AnalysisMode,
    AnalysisResponse,
    Source,
)
from app.services.endpoint_inventory import extract_endpoint, normalize_path
from app.services.history_store import HistoryStore


def test_normalize_path_collapses_dynamic_segments():
    assert normalize_path("/api/users/123/orders/456") == "/api/users/{id}/orders/{id}"
    assert normalize_path("/api/items/550e8400-e29b-41d4-a716-446655440000") == "/api/items/{id}"
    assert normalize_path("/api/users/profile") == "/api/users/profile"
    assert normalize_path("/") == "/"


def test_extract_endpoint_parses_method_path_host_and_params():
    request = (
        "POST /api/users/42?expand=roles HTTP/1.1\r\n"
        "Host: example.test\r\n"
        "Content-Type: application/x-www-form-urlencoded\r\n"
        "Cookie: session=[REDACTED]\r\n"
        "Authorization: Bearer [REDACTED]\r\n\r\n"
        "name=alice&role=admin"
    )

    endpoint = extract_endpoint(request, "https://example.test/api/users/42?expand=roles")

    assert endpoint is not None
    assert endpoint.method == "POST"
    assert endpoint.host == "example.test"
    assert endpoint.path_template == "/api/users/{id}"
    assert endpoint.param_names == ["expand", "name", "role"]
    assert endpoint.has_cookie is True
    assert endpoint.has_auth_header is True


def test_extract_endpoint_parses_json_body_keys_and_host_header_fallback():
    request = (
        "PUT /graphql HTTP/1.1\r\n"
        "Host: api.example.test:8443\r\n"
        "Content-Type: application/json\r\n\r\n"
        '{"query": "x", "variables": {"id": 1}}'
    )

    endpoint = extract_endpoint(request, None)

    assert endpoint is not None
    assert endpoint.host == "api.example.test"
    assert endpoint.path_template == "/graphql"
    assert endpoint.param_names == ["query", "variables"]
    assert endpoint.has_cookie is False


def test_extract_endpoint_returns_none_for_garbage():
    assert extract_endpoint("", None) is None
    assert extract_endpoint("not-an-http-request", None) is None


def test_save_records_endpoint_even_without_findings(tmp_path):
    store = HistoryStore(Database(tmp_path))
    analysis = AnalysisResponse(
        analysis_id=store.create_analysis_id(),
        summary="no issues",
        findings=[],
        redaction_applied=True,
        llm_status="ok",
    )

    store.save(
        source=Source.BURP,
        mode=AnalysisMode.RECON,
        target_url="https://shop.test/upload",
        request_text="POST /upload HTTP/1.1\r\nHost: shop.test\r\nContent-Type: multipart/form-data\r\n\r\n",
        response_text="HTTP/1.1 200 OK\r\n\r\nok",
        metadata=AnalysisMetadata(),
        analysis=analysis,
    )

    endpoints = store.list_endpoints(host="shop.test")
    assert len(endpoints) == 1
    assert endpoints[0]["method"] == "POST"
    assert endpoints[0]["path_template"] == "/upload"
    assert endpoints[0]["analysis_id"] == analysis.analysis_id
