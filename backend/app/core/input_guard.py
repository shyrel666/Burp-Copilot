from __future__ import annotations

from urllib.parse import urlparse

from app.models.schemas import AnalysisMetadata, BodyOmittedReason, ContentEncoding, GuardedPayload


MAX_TOTAL_CHARS = 256 * 1024
STATIC_EXTENSIONS = {
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".map",
    ".png",
    ".svg",
    ".woff",
    ".woff2",
}


def guard_payload(
    request_text: str,
    response_text: str | None,
    target_url: str | None,
    metadata: AnalysisMetadata,
) -> GuardedPayload:
    guarded_metadata = metadata.model_copy(deep=True)
    guarded_request = request_text
    guarded_response = response_text

    if _is_static_resource(target_url, request_text):
        guarded_response = None
        guarded_metadata.body_omitted_reason = BodyOmittedReason.STATIC_RESOURCE
        return GuardedPayload(request_text=guarded_request, response_text=guarded_response, metadata=guarded_metadata)

    if guarded_metadata.content_encoding != ContentEncoding.UTF_8:
        guarded_request = _omit_body(guarded_request, "non-utf8 content")
        guarded_response = _omit_body(guarded_response, "non-utf8 content")
        guarded_metadata.body_omitted_reason = BodyOmittedReason.BINARY
        return GuardedPayload(request_text=guarded_request, response_text=guarded_response, metadata=guarded_metadata)

    if _has_binary_body(guarded_request) or _has_binary_body(guarded_response):
        guarded_request = _omit_body(guarded_request, "binary content")
        guarded_response = _omit_body(guarded_response, "binary content")
        guarded_metadata.body_omitted_reason = BodyOmittedReason.BINARY
        return GuardedPayload(request_text=guarded_request, response_text=guarded_response, metadata=guarded_metadata)

    total = len(guarded_request) + len(guarded_response or "")
    if total > MAX_TOTAL_CHARS:
        guarded_request, request_truncated = _truncate(guarded_request, MAX_TOTAL_CHARS)
        remaining = max(0, MAX_TOTAL_CHARS - len(guarded_request))
        guarded_response, response_truncated = _truncate(guarded_response, remaining)
        guarded_metadata.request_truncated = request_truncated
        guarded_metadata.response_truncated = response_truncated
        guarded_metadata.body_omitted_reason = BodyOmittedReason.TOO_LARGE

    return GuardedPayload(request_text=guarded_request, response_text=guarded_response, metadata=guarded_metadata)


def _is_static_resource(target_url: str | None, request_text: str) -> bool:
    path = urlparse(target_url or "").path
    if not path:
        first_line = request_text.splitlines()[0] if request_text.splitlines() else ""
        parts = first_line.split()
        path = parts[1] if len(parts) >= 2 else ""
    return any(path.lower().split("?", 1)[0].endswith(ext) for ext in STATIC_EXTENSIONS)


def _has_binary_body(text: str | None) -> bool:
    if not text:
        return False
    body = _split_headers_body(text)[1]
    return any(ord(char) < 32 and char not in "\r\n\t" for char in body)


def _omit_body(text: str | None, reason: str) -> str | None:
    if text is None:
        return None
    headers, body = _split_headers_body(text)
    if not body:
        return text
    separator = "\r\n\r\n" if "\r\n\r\n" in text else "\n\n"
    return f"{headers}{separator}[body omitted: {reason}]"


def _split_headers_body(text: str) -> tuple[str, str]:
    if "\r\n\r\n" in text:
        return tuple(text.split("\r\n\r\n", 1))  # type: ignore[return-value]
    if "\n\n" in text:
        return tuple(text.split("\n\n", 1))  # type: ignore[return-value]
    return text, ""


def _truncate(text: str | None, limit: int) -> tuple[str | None, bool]:
    if text is None:
        return None, False
    if len(text) <= limit:
        return text, False
    marker = "\n[truncated: too_large]"
    cutoff = max(0, limit - len(marker))
    return text[:cutoff] + marker, True

