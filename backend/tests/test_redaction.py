from app.core.redaction import redact_http_text, redact_url


def test_redacts_sensitive_headers_and_body_fields():
    raw = "\r\n".join(
        [
            "POST /login HTTP/1.1",
            "Host: example.test",
            "Authorization: Bearer real-token-value",
            "Cookie: sessionid=abc123; theme=dark",
            "X-API-Key: key-123456",
            "Content-Type: application/json",
            "",
            '{"username":"alice","password":"secret-pass","api_key":"secret-api"}',
        ]
    )

    redacted = redact_http_text(raw)

    assert "real-token-value" not in redacted
    assert "sessionid=abc123" not in redacted
    assert "key-123456" not in redacted
    assert "secret-pass" not in redacted
    assert "secret-api" not in redacted
    assert "Authorization: [REDACTED]" in redacted
    assert '"password":"[REDACTED]"' in redacted


def test_redact_url_masks_sensitive_query_params():
    url = "https://example.test/callback?code=abc123&token=def456&view=profile"
    redacted = redact_url(url)
    assert "abc123" not in redacted
    assert "def456" not in redacted
    assert "code=[REDACTED]" in redacted
    assert "token=[REDACTED]" in redacted
    assert "view=profile" in redacted


def test_redact_url_preserves_non_sensitive_params():
    url = "https://example.test/page?page=2&sort=name"
    assert redact_url(url) == url


def test_redact_url_handles_no_query_string():
    url = "https://example.test/path"
    assert redact_url(url) == url


def test_redact_url_returns_none_for_none():
    assert redact_url(None) is None


def test_redact_url_masks_session_and_api_key_params():
    url = "https://example.test/api?session_id=s3cr3t&api_key=k3y123&format=json"
    redacted = redact_url(url)
    assert "s3cr3t" not in redacted
    assert "k3y123" not in redacted
    assert "session_id=[REDACTED]" in redacted
    assert "api_key=[REDACTED]" in redacted
    assert "format=json" in redacted
