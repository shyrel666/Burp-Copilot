"""Extract a structured endpoint/parameter inventory from captured HTTP traffic.

This is the structural backbone of "attack surface": every analyzed request
contributes an endpoint entry (host / method / normalized path / parameter
names / content-type / auth indicators) regardless of whether a finding was
produced. Only parameter *names* are kept here, never values, and the input is
already-redacted traffic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class ExtractedEndpoint:
    host: str | None
    method: str
    path_template: str
    param_names: list[str]
    content_type: str | None
    has_cookie: bool
    has_auth_header: bool


_NUM_RE = re.compile(r"^\d+$")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_LONG_HEX_RE = re.compile(r"^[0-9a-fA-F]{16,}$")


def normalize_path(path: str) -> str:
    """Collapse dynamic identifier segments to ``{id}`` so the same endpoint
    surfaces as one template regardless of the concrete id."""
    if not path:
        return "/"
    segments = path.split("/")
    normalized = []
    for seg in segments:
        if seg and (_NUM_RE.match(seg) or _UUID_RE.match(seg) or _LONG_HEX_RE.match(seg)):
            normalized.append("{id}")
        else:
            normalized.append(seg)
    result = "/".join(normalized)
    return result or "/"


def _resolve_host(target_url: str | None, header_host: str | None) -> str | None:
    if target_url:
        candidate = target_url if "://" in target_url else f"http://{target_url}"
        host = urlparse(candidate).hostname
        if host:
            return host.lower()
    if header_host:
        return header_host.split(":")[0].strip().lower() or None
    return None


def _param_names_from_query(query: str) -> set[str]:
    if not query:
        return set()
    return set(parse_qs(query, keep_blank_values=True).keys())


def _param_names_from_body(body: str, content_type: str | None) -> set[str]:
    body = body.strip()
    if not body:
        return set()
    ctype = (content_type or "").lower()
    if "application/x-www-form-urlencoded" in ctype:
        return set(parse_qs(body, keep_blank_values=True).keys())
    if "json" in ctype:
        try:
            parsed = json.loads(body)
        except (ValueError, TypeError):
            return set()
        if isinstance(parsed, dict):
            return {str(key) for key in parsed.keys()}
    return set()


def extract_endpoint(request_text: str, target_url: str | None) -> ExtractedEndpoint | None:
    """Parse a raw (already-redacted) HTTP request into an endpoint entry.

    Returns ``None`` when the text does not look like an HTTP request line.
    """
    if not request_text or not request_text.strip():
        return None

    normalized = request_text.replace("\r\n", "\n")
    head, _, body = normalized.partition("\n\n")
    lines = head.split("\n")
    request_line = lines[0].strip()
    parts = request_line.split()
    if len(parts) < 2:
        return None

    method = parts[0].upper()
    raw_target = parts[1]

    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()

    if "://" in raw_target:
        parsed_target = urlparse(raw_target)
        path_part = parsed_target.path or "/"
        query_part = parsed_target.query
    else:
        path_part, _, query_part = raw_target.partition("?")

    param_names: set[str] = set()
    param_names |= _param_names_from_query(query_part)
    if target_url and "?" in target_url:
        param_names |= _param_names_from_query(urlparse(target_url).query)

    content_type = headers.get("content-type")
    param_names |= _param_names_from_body(body, content_type)

    return ExtractedEndpoint(
        host=_resolve_host(target_url, headers.get("host")),
        method=method,
        path_template=normalize_path(path_part or "/"),
        param_names=sorted(param_names),
        content_type=content_type,
        has_cookie="cookie" in headers,
        has_auth_header="authorization" in headers,
    )
