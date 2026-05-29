from app.models.schemas import (
    AnalysisMetadata,
    AnalysisMode,
    AnalysisResponse,
    Source,
)
from app.services.fingerprint_service import FingerprintService
from app.services.history_store import HistoryStore


def _save(store, *, target_url, request_text, response_text):
    analysis = AnalysisResponse(
        analysis_id=store.create_analysis_id(),
        summary="x",
        findings=[],
        redaction_applied=True,
        llm_status="ok",
    )
    store.save(
        source=Source.BURP,
        mode=AnalysisMode.RECON,
        target_url=target_url,
        request_text=request_text,
        response_text=response_text,
        metadata=AnalysisMetadata(),
        analysis=analysis,
    )


def test_unknown_host_returns_unknown_profile(tmp_path):
    service = FingerprintService(HistoryStore(tmp_path))
    profile = service.fingerprint("nope.test")
    assert profile.system_types == ["unknown"]
    assert profile.endpoint_count == 0


def test_detects_wordpress_and_cookie_session(tmp_path):
    store = HistoryStore(tmp_path)
    _save(
        store,
        target_url="https://blog.test/wp-login.php",
        request_text="POST /wp-login.php HTTP/1.1\r\nHost: blog.test\r\nCookie: wordpress_test=[REDACTED]\r\n\r\nlog=admin",
        response_text="HTTP/1.1 200 OK\r\nServer: Apache\r\nSet-Cookie: wordpress_logged_in=[REDACTED]\r\n\r\n<html></html>",
    )

    profile = FingerprintService(store).fingerprint("blog.test")

    assert "cms_wordpress" in profile.system_types
    assert "cookie_session" in profile.auth_methods
    assert "Apache" in profile.tech_stack
    assert profile.confidence > 0.1


def test_detects_rest_api_with_bearer_token(tmp_path):
    store = HistoryStore(tmp_path)
    _save(
        store,
        target_url="https://api.test/api/users/1",
        request_text="GET /api/users/1 HTTP/1.1\r\nHost: api.test\r\nAuthorization: Bearer [REDACTED]\r\n\r\n",
        response_text="HTTP/1.1 200 OK\r\nX-Powered-By: Express\r\nContent-Type: application/json\r\n\r\n{}",
    )

    profile = FingerprintService(store).fingerprint("api.test")

    assert "rest_api" in profile.system_types
    assert "bearer_token" in profile.auth_methods
    assert "Express" in profile.tech_stack


def test_detects_graphql_and_spa(tmp_path):
    store = HistoryStore(tmp_path)
    _save(
        store,
        target_url="https://app.test/graphql",
        request_text="POST /graphql HTTP/1.1\r\nHost: app.test\r\nContent-Type: application/json\r\n\r\n{\"query\":\"x\"}",
        response_text="HTTP/1.1 200 OK\r\n\r\n{}",
    )
    _save(
        store,
        target_url="https://app.test/",
        request_text="GET / HTTP/1.1\r\nHost: app.test\r\n\r\n",
        response_text="HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body><div id=\"root\"></div></body></html>",
    )

    profile = FingerprintService(store).fingerprint("app.test")

    assert "graphql" in profile.system_types
    assert "spa" in profile.system_types
