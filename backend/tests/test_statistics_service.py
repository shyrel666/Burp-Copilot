import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app
from app.core.database import Database
from app.models.schemas import (
    AnalysisMetadata,
    AnalysisMode,
    AnalysisResponse,
    Finding,
    Source,
)
from app.services.history_store import HistoryStore
from app.services.statistics_service import StatisticsService


def _finding(severity="medium", owasp=None, **kw):
    base = dict(
        title="t",
        severity=severity,
        confidence=0.5,
        evidence="e",
        attack_approach="a",
        remediation="r",
        owasp_category=owasp,
    )
    base.update(kw)
    return Finding.model_validate(base)


def _save(store, *, findings, llm_status="ok", target_url="https://x.test/a", request_text=None):
    analysis = AnalysisResponse(
        analysis_id=store.create_analysis_id(),
        summary="s",
        findings=findings,
        redaction_applied=True,
        llm_status=llm_status,
    )
    store.save(
        source=Source.DASHBOARD,
        mode=AnalysisMode.RECON,
        target_url=target_url,
        request_text=request_text or "GET /a HTTP/1.1\r\nHost: x.test\r\n\r\n",
        response_text="HTTP/1.1 200 OK\r\n\r\nok",
        metadata=AnalysisMetadata(),
        analysis=analysis,
    )


def test_empty_history_returns_zeros(tmp_path):
    service = StatisticsService(HistoryStore(Database(tmp_path)))
    stats = service.get_statistics()
    assert stats.total_analyses == 0
    assert stats.success_rate == 0.0
    assert stats.top_vulnerability_types == []
    assert service.get_recent_findings() == []
    assert service.get_attack_surface().total_endpoints == 0


def test_statistics_aggregates_severity_success_and_top_types(tmp_path):
    store = HistoryStore(Database(tmp_path))
    _save(store, findings=[_finding("high", "A01"), _finding("low", "A01")], llm_status="ok")
    _save(store, findings=[_finding("critical", "A03")], llm_status="repaired")
    _save(store, findings=[], llm_status="failed")

    stats = StatisticsService(store).get_statistics()
    assert stats.total_analyses == 3
    assert stats.success_rate == 2 / 3
    assert stats.severity_distribution.high == 1
    assert stats.severity_distribution.low == 1
    assert stats.severity_distribution.critical == 1
    assert stats.top_vulnerability_types[0].owasp_category == "A01"
    assert stats.top_vulnerability_types[0].count == 2


def test_attack_surface_includes_endpoints_without_findings(tmp_path):
    store = HistoryStore(Database(tmp_path))
    _save(
        store,
        findings=[],
        target_url="https://x.test/upload",
        request_text="POST /upload HTTP/1.1\r\nHost: x.test\r\nCookie: s=[REDACTED]\r\n\r\nfile=x",
    )

    surface = StatisticsService(store).get_attack_surface()
    assert surface.total_endpoints == 1
    endpoint = surface.endpoints[0]
    assert endpoint.path_template == "/upload"
    assert endpoint.finding_count == 0
    assert endpoint.has_auth_boundary is True
    assert endpoint.priority_score > 0


def test_attack_surface_ranks_higher_severity_and_write_methods_first(tmp_path):
    store = HistoryStore(Database(tmp_path))
    _save(
        store,
        findings=[_finding("critical")],
        target_url="https://x.test/admin",
        request_text="POST /admin HTTP/1.1\r\nHost: x.test\r\nAuthorization: Bearer [REDACTED]\r\n\r\nx=1",
    )
    _save(
        store,
        findings=[],
        target_url="https://x.test/about",
        request_text="GET /about HTTP/1.1\r\nHost: x.test\r\n\r\n",
    )

    surface = StatisticsService(store).get_attack_surface()
    assert surface.endpoints[0].path_template == "/admin"


def _insert(db_path, *, created_at, llm_status, findings):
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO analysis_history (
                analysis_id, created_at, source, mode, target_url, request_text,
                response_text, metadata_json, summary, findings_json,
                redaction_applied, llm_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                created_at,
                "dashboard",
                "recon",
                "https://x.test/a",
                "GET /a HTTP/1.1\r\nHost: x.test\r\n\r\n",
                None,
                AnalysisMetadata().model_dump_json(),
                "s",
                __import__("json").dumps([f.model_dump(mode="json") for f in findings]),
                1,
                llm_status,
            ),
        )


def test_since_filter_restricts_statistics(tmp_path):
    store = HistoryStore(Database(tmp_path))
    _insert(store.db_path, created_at="2020-01-01T00:00:00+00:00", llm_status="ok", findings=[_finding("low")])
    _insert(store.db_path, created_at="2026-01-01T00:00:00+00:00", llm_status="ok", findings=[_finding("high")])

    stats = StatisticsService(store).get_statistics(since="2025-01-01T00:00:00+00:00")
    assert stats.total_analyses == 1
    assert stats.severity_distribution.high == 1
    assert stats.severity_distribution.low == 0


# --- API integration ---


def test_statistics_api_empty_and_invalid_since(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)

    empty = client.get("/api/v1/statistics")
    assert empty.status_code == 200
    assert empty.json()["total_analyses"] == 0

    bad = client.get("/api/v1/statistics", params={"since": "not-a-date"})
    assert bad.status_code == 422

    surface = client.get("/api/v1/statistics/attack-surface")
    assert surface.status_code == 200
    assert surface.json()["total_endpoints"] == 0

    recent = client.get("/api/v1/statistics/recent-findings", params={"limit": 5})
    assert recent.status_code == 200
    assert recent.json() == []


def test_architecture_api_returns_unknown_for_unseen_host(tmp_path):
    app = create_app(data_dir=tmp_path, provider_mode="fake")
    client = TestClient(app)
    resp = client.get("/api/v1/recon/architecture", params={"host": "nobody.test"})
    assert resp.status_code == 200
    assert resp.json()["system_types"] == ["unknown"]
