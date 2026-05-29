"""Deterministic architecture/technology fingerprinting for a host.

Different Web system types have very different attack surfaces, so before the
roadmap stage we classify what kind of system we are looking at. This uses
rule-based detection over already-captured (and redacted) traffic: endpoint
inventory, surviving response headers (Server / X-Powered-By / Via / generator)
and request auth indicators. Redaction keeps header *names* (so the presence of
Cookie / Authorization / Set-Cookie is still observable) and non-sensitive
headers like Server, so these signals remain reliable.

Intelligence that requires reasoning (the staged testing roadmap) is handled by
the LLM in a later stage; fingerprinting stays deterministic for reliability.
"""

from __future__ import annotations

import re

from app.models.schemas import ArchitectureProfile
from app.services.history_store import HistoryStore


_TECH_HEADER_NAMES = ("server", "x-powered-by", "x-aspnet-version", "x-generator", "x-runtime")
_GATEWAY_HEADER_HINTS = ("via", "x-envoy", "x-kong", "x-amzn", "x-amz-cf", "x-istio")
_GATEWAY_SERVER_HINTS = ("kong", "envoy", "istio", "traefik", "apigee")


def _parse_response_headers(response_text: str | None) -> dict[str, list[str]]:
    if not response_text:
        return {}
    head = response_text.replace("\r\n", "\n").split("\n\n", 1)[0]
    headers: dict[str, list[str]] = {}
    for line in head.split("\n")[1:]:
        if ":" in line:
            key, _, value = line.partition(":")
            headers.setdefault(key.strip().lower(), []).append(value.strip())
    return headers


class FingerprintService:
    def __init__(self, history: HistoryStore):
        self.history = history

    def fingerprint(self, host: str) -> ArchitectureProfile:
        host = (host or "").lower().strip()
        endpoints = self.history.list_endpoints(host=host)
        if not endpoints:
            return ArchitectureProfile(host=host or None, system_types=["unknown"])

        items = self.history.list(target_host=host, limit=500)
        paths = [e["path_template"] for e in endpoints]
        param_names = {p.lower() for e in endpoints for p in e["param_names"]}
        has_auth_header = any(e["has_auth_header"] for e in endpoints)
        has_cookie = any(e["has_cookie"] for e in endpoints)

        response_headers: dict[str, list[str]] = {}
        response_bodies: list[str] = []
        has_set_cookie = False
        for item in items:
            headers = _parse_response_headers(item.response_text)
            for name, values in headers.items():
                response_headers.setdefault(name, []).extend(values)
            if "set-cookie" in headers:
                has_set_cookie = True
            if item.response_text:
                response_bodies.append(item.response_text.lower())

        system_types: list[str] = []
        auth_methods: list[str] = []
        tech_stack: list[str] = []
        evidence: list[str] = []

        self._detect_system_types(paths, response_headers, response_bodies, system_types, evidence)
        self._detect_auth_methods(
            paths, param_names, has_auth_header, has_cookie, has_set_cookie, auth_methods, evidence
        )
        self._detect_tech_stack(response_headers, tech_stack, evidence)

        if not system_types:
            system_types.append("unknown")

        confidence = self._estimate_confidence(system_types, evidence, len(endpoints))

        return ArchitectureProfile(
            host=host,
            system_types=system_types,
            auth_methods=auth_methods,
            tech_stack=sorted(set(tech_stack)),
            evidence=evidence,
            endpoint_count=len(endpoints),
            confidence=confidence,
        )

    def _detect_system_types(self, paths, response_headers, response_bodies, system_types, evidence):
        joined_paths = " ".join(paths).lower()

        if any("graphql" in p.lower() for p in paths):
            system_types.append("graphql")
            evidence.append("发现 GraphQL 端点（路径含 graphql）")

        if re.search(r"(^|\s)/api(/|\s|$)", joined_paths) or "/api/" in joined_paths or "/rest/" in joined_paths:
            system_types.append("rest_api")
            evidence.append("存在 /api 风格端点，疑似 REST API")

        if any(h in joined_paths for h in ("wp-admin", "wp-content", "wp-json", "wp-login", "xmlrpc.php")):
            system_types.append("cms_wordpress")
            evidence.append("命中 WordPress 特征路径（wp-*）")

        if "drupal" in " ".join(response_headers.get("x-generator", [])).lower() or "/sites/default" in joined_paths:
            system_types.append("cms_drupal")
            evidence.append("命中 Drupal 特征（X-Generator 或 /sites/default）")

        if any(re.search(r"\.(php|jsp|aspx?|do)(\b|/|\{)", p.lower()) for p in paths):
            system_types.append("mpa")
            evidence.append("存在服务端页面扩展名（.php/.jsp/.aspx 等），疑似传统 MPA")

        if any(
            re.search(r'<div\s+id=["\'](root|app)["\']', body) or "window.__nuxt__" in body or "window.__next_data__" in body
            for body in response_bodies
        ):
            if "spa" not in system_types:
                system_types.append("spa")
                evidence.append("响应含 SPA 挂载点（#root/#app 或框架运行时），疑似单页应用")

        gateway = False
        for hint in _GATEWAY_HEADER_HINTS:
            if any(name.startswith(hint) for name in response_headers):
                gateway = True
        server_values = " ".join(response_headers.get("server", [])).lower()
        if any(s in server_values for s in _GATEWAY_SERVER_HINTS):
            gateway = True
        if gateway:
            system_types.append("microservice_gateway")
            evidence.append("响应头出现网关/代理特征（Via/Envoy/Kong 等）")

    def _detect_auth_methods(
        self, paths, param_names, has_auth_header, has_cookie, has_set_cookie, auth_methods, evidence
    ):
        joined_paths = " ".join(paths).lower()
        if has_auth_header:
            auth_methods.append("bearer_token")
            evidence.append("请求携带 Authorization 头（Bearer/JWT 类令牌认证）")
        if has_cookie or has_set_cookie:
            auth_methods.append("cookie_session")
            evidence.append("使用 Cookie 会话（请求 Cookie 或响应 Set-Cookie）")
        if (
            any(h in joined_paths for h in ("/oauth", "/authorize", "/token", "/callback", "/connect/"))
            or {"code", "state", "id_token"} & param_names
        ):
            auth_methods.append("oauth")
            evidence.append("命中 OAuth/OIDC 特征（授权路径或 code/state 参数）")

    def _detect_tech_stack(self, response_headers, tech_stack, evidence):
        for name in _TECH_HEADER_NAMES:
            for value in response_headers.get(name, []):
                if value:
                    tech_stack.append(value)
                    evidence.append(f"技术栈指纹：{name}: {value}")

    @staticmethod
    def _estimate_confidence(system_types, evidence, endpoint_count) -> float:
        if system_types == ["unknown"]:
            return 0.1
        score = 0.3 + 0.1 * len(evidence) + min(endpoint_count, 10) * 0.02
        return round(min(score, 0.95), 2)
