"""Property tests for the statistics service.

Feature: dashboard-overview-auto-analysis
"""

import json
import sqlite3

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.core.database import Database
from app.models.schemas import AnalysisMetadata
from app.services.history_store import HistoryStore
from app.services.statistics_service import StatisticsService


_SEVERITIES = ["critical", "high", "medium", "low", "info"]
_STATUSES = ["ok", "repaired", "failed"]


def _finding_dict(severity, owasp):
    return {
        "title": "t",
        "severity": severity,
        "confidence": 0.5,
        "evidence": "e",
        "attack_approach": "a",
        "remediation": "r",
        "owasp_category": owasp,
    }


_finding_strategy = st.builds(
    _finding_dict,
    severity=st.sampled_from(_SEVERITIES),
    owasp=st.one_of(st.none(), st.sampled_from(["A01", "A02", "A03", "A04", "A05", "A06"])),
)

_analysis_strategy = st.fixed_dictionaries(
    {
        "created_at": st.integers(min_value=2000, max_value=2030).map(
            lambda y: f"{y}-01-01T00:00:00+00:00"
        ),
        "llm_status": st.sampled_from(_STATUSES),
        "findings": st.lists(_finding_strategy, max_size=6),
    }
)


def _insert(db_path, analyses):
    with sqlite3.connect(db_path) as conn:
        for index, a in enumerate(analyses):
            conn.execute(
                """
                INSERT INTO analysis_history (
                    analysis_id, created_at, source, mode, target_url, request_text,
                    response_text, metadata_json, summary, findings_json,
                    redaction_applied, llm_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"id-{index}",
                    a["created_at"],
                    "dashboard",
                    "recon",
                    "https://x.test/a",
                    "GET /a HTTP/1.1\r\nHost: x.test\r\n\r\n",
                    None,
                    AnalysisMetadata().model_dump_json(),
                    "s",
                    json.dumps(a["findings"]),
                    1,
                    a["llm_status"],
                ),
            )


_settings = settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


# Property 1: Severity distribution sum equals total findings
@_settings
@given(analyses=st.lists(_analysis_strategy, max_size=30))
def test_property_severity_distribution_sum(tmp_path_factory, analyses):
    store = HistoryStore(Database(tmp_path_factory.mktemp("p1")))
    _insert(store.db_path, analyses)
    stats = StatisticsService(store).get_statistics()
    dist = stats.severity_distribution
    total_findings = sum(len(a["findings"]) for a in analyses)
    assert dist.critical + dist.high + dist.medium + dist.low + dist.info == total_findings


# Property 2: Success rate formula correctness
@_settings
@given(analyses=st.lists(_analysis_strategy, min_size=1, max_size=30))
def test_property_success_rate_formula(tmp_path_factory, analyses):
    store = HistoryStore(Database(tmp_path_factory.mktemp("p2")))
    _insert(store.db_path, analyses)
    stats = StatisticsService(store).get_statistics()
    success = sum(1 for a in analyses if a["llm_status"] in ("ok", "repaired"))
    assert abs(stats.success_rate - success / len(analyses)) < 1e-9


# Property 3: Top vulnerability types ranking
@_settings
@given(analyses=st.lists(_analysis_strategy, max_size=30))
def test_property_top_types_ranking(tmp_path_factory, analyses):
    store = HistoryStore(Database(tmp_path_factory.mktemp("p3")))
    _insert(store.db_path, analyses)
    top = StatisticsService(store).get_statistics().top_vulnerability_types
    counts = [t.count for t in top]
    assert counts == sorted(counts, reverse=True)
    assert len(top) <= 5

    expected: dict[str, int] = {}
    for a in analyses:
        for f in a["findings"]:
            if f["owasp_category"]:
                expected[f["owasp_category"]] = expected.get(f["owasp_category"], 0) + 1
    if expected:
        max_omitted = 0
        returned_names = {t.owasp_category for t in top}
        for name, count in expected.items():
            if name not in returned_names:
                max_omitted = max(max_omitted, count)
        assert all(t.count >= max_omitted for t in top)


# Property 4: Since filter restricts computation scope
@_settings
@given(
    analyses=st.lists(_analysis_strategy, max_size=30),
    since_year=st.integers(min_value=2000, max_value=2030),
)
def test_property_since_filter(tmp_path_factory, analyses, since_year):
    store = HistoryStore(Database(tmp_path_factory.mktemp("p4")))
    _insert(store.db_path, analyses)
    since = f"{since_year}-01-01T00:00:00+00:00"
    stats = StatisticsService(store).get_statistics(since=since)
    expected_total = sum(1 for a in analyses if a["created_at"] >= since)
    assert stats.total_analyses == expected_total


# Property 5: Recent findings ordering and field completeness
@_settings
@given(analyses=st.lists(_analysis_strategy, max_size=30), limit=st.integers(min_value=1, max_value=100))
def test_property_recent_findings_ordering(tmp_path_factory, analyses, limit):
    store = HistoryStore(Database(tmp_path_factory.mktemp("p5")))
    _insert(store.db_path, analyses)
    recent = StatisticsService(store).get_recent_findings(limit=limit)

    assert len(recent) <= limit
    timestamps = [r.created_at for r in recent]
    assert timestamps == sorted(timestamps, reverse=True)
    for r in recent:
        assert r.title and r.severity and r.analysis_id and r.created_at
