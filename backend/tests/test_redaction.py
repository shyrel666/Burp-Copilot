from app.core.redaction import redact_http_text


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
