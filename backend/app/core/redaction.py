from __future__ import annotations

import re
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse


SENSITIVE_HEADER_PATTERN = re.compile(
    r"^(Authorization|Cookie|Set-Cookie|X-API-Key|X-Auth-Token|Proxy-Authorization)\s*:\s*.*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

JSON_SECRET_FIELD_PATTERN = re.compile(
    r'("(?:password|passwd|token|access_token|refresh_token|secret|api_key|apikey|session)"\s*:\s*)"[^"]*"',
    flags=re.IGNORECASE,
)

FORM_SECRET_FIELD_PATTERN = re.compile(
    r"\b(password|passwd|token|access_token|refresh_token|secret|api_key|apikey|session)=([^&\s]+)",
    flags=re.IGNORECASE,
)

SENSITIVE_QUERY_PARAMS = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "session",
        "session_id",
        "sessionid",
        "code",
        "api_key",
        "apikey",
        "secret",
        "password",
        "passwd",
        "auth",
        "authorization",
        "id_token",
        "state",
    }
)


def redact_url(url: str | None) -> str | None:
    if url is None:
        return None
    parsed = urlparse(url)
    if not parsed.query:
        return url
    qs = parse_qs(parsed.query, keep_blank_values=True)
    redacted_qs: dict[str, list[str]] = {}
    for key, values in qs.items():
        if key.lower() in SENSITIVE_QUERY_PARAMS:
            redacted_qs[key] = ["[REDACTED]"]
        else:
            redacted_qs[key] = values
    new_query = urlencode(redacted_qs, doseq=True, safe="[]", quote_via=quote)
    return urlunparse(parsed._replace(query=new_query))


def redact_http_text(text: str | None) -> str | None:
    if text is None:
        return None

    redacted = SENSITIVE_HEADER_PATTERN.sub(lambda match: f"{match.group(1)}: [REDACTED]", text)
    redacted = JSON_SECRET_FIELD_PATTERN.sub(lambda match: f'{match.group(1)}"[REDACTED]"', redacted)
    redacted = FORM_SECRET_FIELD_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    return redacted


def redact_pair(request_text: str, response_text: str | None) -> tuple[str, str | None]:
    return redact_http_text(request_text) or "", redact_http_text(response_text)

