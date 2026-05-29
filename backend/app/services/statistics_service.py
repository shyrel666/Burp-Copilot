"""Aggregate analysis history into security-posture statistics and an attack
surface view.

Computations run in Python over the (small, local) history rather than relying
on SQLite JSON functions, so behavior is identical regardless of the SQLite
build. The attack surface deliberately includes endpoints that produced *no*
finding, because an untested endpoint is exactly where a beginner should be
pointed next.
"""

from __future__ import annotations

from app.models.schemas import (
    AttackSurfaceEndpoint,
    AttackSurfaceResponse,
    RecentFinding,
    SeverityDistribution,
    StatisticsResponse,
    TopVulnerabilityType,
)
from app.services.history_store import HistoryStore


_SEVERITY_RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
_SUCCESS_STATUSES = {"ok", "repaired"}
_WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
_LARGE_LIMIT = 100_000


class StatisticsService:
    def __init__(self, history: HistoryStore):
        self.history = history

    def get_statistics(self, since: str | None = None) -> StatisticsResponse:
        items = self.history.list(since=since, limit=_LARGE_LIMIT)
        total = len(items)

        distribution = SeverityDistribution()
        category_counts: dict[str, int] = {}
        success = 0
        for item in items:
            if item.llm_status in _SUCCESS_STATUSES:
                success += 1
            for finding in item.findings:
                setattr(
                    distribution,
                    finding.severity.value,
                    getattr(distribution, finding.severity.value) + 1,
                )
                if finding.owasp_category:
                    category_counts[finding.owasp_category] = (
                        category_counts.get(finding.owasp_category, 0) + 1
                    )

        success_rate = (success / total) if total else 0.0
        top = sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
        return StatisticsResponse(
            total_analyses=total,
            success_rate=success_rate,
            severity_distribution=distribution,
            top_vulnerability_types=[
                TopVulnerabilityType(owasp_category=name, count=count) for name, count in top
            ],
        )

    def get_recent_findings(self, limit: int = 20) -> list[RecentFinding]:
        items = self.history.list(limit=_LARGE_LIMIT)  # already ordered created_at DESC
        recent: list[RecentFinding] = []
        for item in items:
            for finding in item.findings:
                recent.append(
                    RecentFinding(
                        title=finding.title,
                        severity=finding.severity,
                        confidence=finding.confidence,
                        owasp_category=finding.owasp_category,
                        analysis_id=item.analysis_id,
                        target_url=item.target_url,
                        created_at=item.created_at,
                    )
                )
                if len(recent) >= limit:
                    return recent
        return recent

    def get_attack_surface(self, host: str | None = None, limit: int = 50) -> AttackSurfaceResponse:
        findings_by_analysis = {
            item.analysis_id: item.findings
            for item in self.history.list(limit=_LARGE_LIMIT)
        }
        endpoints = self.history.list_endpoints(host=host)

        grouped: dict[tuple, dict] = {}
        for entry in endpoints:
            key = (entry["host"], entry["method"], entry["path_template"])
            group = grouped.setdefault(
                key,
                {
                    "host": entry["host"],
                    "method": entry["method"],
                    "path_template": entry["path_template"],
                    "hit_count": 0,
                    "param_names": set(),
                    "has_auth_boundary": False,
                    "finding_count": 0,
                    "max_rank": 0,
                },
            )
            group["hit_count"] += 1
            group["param_names"].update(entry["param_names"])
            group["has_auth_boundary"] = group["has_auth_boundary"] or entry["has_cookie"] or entry["has_auth_header"]
            for finding in findings_by_analysis.get(entry["analysis_id"], []):
                group["finding_count"] += 1
                group["max_rank"] = max(group["max_rank"], _SEVERITY_RANK.get(finding.severity.value, 0))

        result: list[AttackSurfaceEndpoint] = []
        for group in grouped.values():
            max_severity = next(
                (sev for sev, rank in _SEVERITY_RANK.items() if rank == group["max_rank"]),
                None,
            )
            score = self._priority_score(group)
            result.append(
                AttackSurfaceEndpoint(
                    host=group["host"],
                    method=group["method"],
                    path_template=group["path_template"],
                    hit_count=group["hit_count"],
                    param_names=sorted(group["param_names"]),
                    has_auth_boundary=group["has_auth_boundary"],
                    finding_count=group["finding_count"],
                    max_severity=max_severity,
                    priority_score=score,
                )
            )

        result.sort(key=lambda e: (-e.priority_score, e.host or "", e.path_template))
        return AttackSurfaceResponse(total_endpoints=len(result), endpoints=result[:limit])

    @staticmethod
    def _priority_score(group: dict) -> float:
        score = float(group["max_rank"])
        score += 0.3 * len(group["param_names"])
        if group["method"] in _WRITE_METHODS:
            score += 1.0
        if group["has_auth_boundary"]:
            score += 1.0
        return round(score, 2)
