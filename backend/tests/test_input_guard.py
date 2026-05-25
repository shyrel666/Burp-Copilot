from app.core.input_guard import guard_payload
from app.models.schemas import AnalysisMetadata, BodyOmittedReason, ContentEncoding


def test_static_resource_response_body_is_omitted():
    request = "GET /assets/app.js HTTP/1.1\r\nHost: example.test\r\n\r\n"
    response = "HTTP/1.1 200 OK\r\nContent-Type: application/javascript\r\n\r\nconsole.log('large asset')"

    guarded = guard_payload(
        request,
        response,
        target_url="https://example.test/assets/app.js",
        metadata=AnalysisMetadata(content_encoding=ContentEncoding.UTF_8),
    )

    assert guarded.response_text is None
    assert guarded.metadata.body_omitted_reason == BodyOmittedReason.STATIC_RESOURCE


def test_oversized_payload_is_truncated_and_marked():
    request = "POST /submit HTTP/1.1\r\nHost: example.test\r\n\r\n" + ("A" * (260 * 1024))

    guarded = guard_payload(
        request,
        None,
        target_url="https://example.test/submit",
        metadata=AnalysisMetadata(content_encoding=ContentEncoding.UTF_8),
    )

    assert len(guarded.request_text) <= 256 * 1024
    assert guarded.metadata.request_truncated is True
    assert guarded.metadata.body_omitted_reason == BodyOmittedReason.TOO_LARGE


def test_binary_like_body_is_omitted():
    request = "POST /upload HTTP/1.1\r\nHost: example.test\r\n\r\nhello\x00\x01\x02world"

    guarded = guard_payload(
        request,
        None,
        target_url="https://example.test/upload",
        metadata=AnalysisMetadata(content_encoding=ContentEncoding.UTF_8),
    )

    assert "\x00" not in guarded.request_text
    assert guarded.metadata.body_omitted_reason == BodyOmittedReason.BINARY
