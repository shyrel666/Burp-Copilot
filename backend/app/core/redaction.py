from __future__ import annotations

import re


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


def redact_http_text(text: str | None) -> str | None:
    if text is None:
        return None

    redacted = SENSITIVE_HEADER_PATTERN.sub(lambda match: f"{match.group(1)}: [REDACTED]", text)
    redacted = JSON_SECRET_FIELD_PATTERN.sub(lambda match: f'{match.group(1)}"[REDACTED]"', redacted)
    redacted = FORM_SECRET_FIELD_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    return redacted


def redact_pair(request_text: str, response_text: str | None) -> tuple[str, str | None]:
    return redact_http_text(request_text) or "", redact_http_text(response_text)

