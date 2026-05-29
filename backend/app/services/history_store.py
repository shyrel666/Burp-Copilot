from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.database import Database
from app.models.schemas import (
    AnalysisHistoryItem,
    AnalysisMetadata,
    AnalysisMode,
    AnalysisResponse,
    Finding,
    Severity,
    Source,
)
from app.services.endpoint_inventory import ExtractedEndpoint, extract_endpoint


SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _top_severity(findings: list[Finding]) -> str | None:
    """Return the highest severity from findings, or None if empty."""
    if not findings:
        return None
    return min(findings, key=lambda f: SEVERITY_RANK.get(f.severity.value, 99)).severity.value


class HistoryStore:
    def __init__(self, db: Database):
        self._db = db
        self._init_db()

    @property
    def db_path(self) -> Path:
        return self._db.db_path

    def save(
        self,
        *,
        source: Source,
        mode: AnalysisMode,
        target_url: str | None,
        request_text: str,
        response_text: str | None,
        metadata: AnalysisMetadata,
        analysis: AnalysisResponse,
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        endpoint = extract_endpoint(request_text, target_url)
        top_sev = _top_severity(analysis.findings)
        with self._db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO analysis_history (
                    analysis_id, created_at, source, mode, target_url, request_text,
                    response_text, metadata_json, summary, findings_json,
                    redaction_applied, llm_status, top_severity
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis.analysis_id,
                    created_at,
                    source.value,
                    mode.value,
                    target_url,
                    request_text,
                    response_text,
                    metadata.model_dump_json(),
                    analysis.summary,
                    json.dumps([finding.model_dump(mode="json") for finding in analysis.findings]),
                    int(analysis.redaction_applied),
                    analysis.llm_status,
                    top_sev,
                ),
            )
            if endpoint is not None:
                self._insert_endpoint(conn, analysis.analysis_id, created_at, endpoint)

    @staticmethod
    def _insert_endpoint(
        conn: sqlite3.Connection,
        analysis_id: str,
        created_at: str,
        endpoint: ExtractedEndpoint,
    ) -> None:
        conn.execute(
            """
            INSERT INTO endpoints (
                analysis_id, created_at, host, method, path_template,
                param_names, content_type, has_cookie, has_auth_header
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                created_at,
                endpoint.host,
                endpoint.method,
                endpoint.path_template,
                json.dumps(endpoint.param_names),
                endpoint.content_type,
                int(endpoint.has_cookie),
                int(endpoint.has_auth_header),
            ),
        )

    def create_analysis_id(self) -> str:
        return str(uuid.uuid4())

    def list(
        self,
        *,
        mode: str | None = None,
        min_severity: str | None = None,
        target_host: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalysisHistoryItem]:
        query = "SELECT * FROM analysis_history WHERE 1=1"
        params: list = []
        if mode:
            query += " AND mode = ?"
            params.append(mode)
        if target_host:
            query += " AND target_url LIKE ?"
            params.append(f"%{target_host}%")
        if since:
            query += " AND created_at >= ?"
            params.append(since)
        if until:
            query += " AND created_at <= ?"
            params.append(until)
        if min_severity:
            min_rank = SEVERITY_RANK.get(min_severity, 99)
            allowed = [s for s, r in SEVERITY_RANK.items() if r <= min_rank]
            placeholders = ",".join("?" * len(allowed))
            query += f" AND top_severity IN ({placeholders})"
            params.extend(allowed)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        conn = self._db.conn
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        return [self._row_to_item(row) for row in rows]

    def list_endpoints(self, *, host: str | None = None) -> list[dict]:
        query = "SELECT * FROM endpoints WHERE 1=1"
        params: list = []
        if host:
            query += " AND host = ?"
            params.append(host.lower())
        query += " ORDER BY created_at ASC"
        conn = self._db.conn
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        return [
            {
                "analysis_id": row["analysis_id"],
                "created_at": row["created_at"],
                "host": row["host"],
                "method": row["method"],
                "path_template": row["path_template"],
                "param_names": json.loads(row["param_names"]),
                "content_type": row["content_type"],
                "has_cookie": bool(row["has_cookie"]),
                "has_auth_header": bool(row["has_auth_header"]),
            }
            for row in rows
        ]

    def get(self, analysis_id: str) -> AnalysisHistoryItem | None:
        conn = self._db.conn
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM analysis_history WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchone()
        return self._row_to_item(row) if row else None

    def _init_db(self) -> None:
        conn = self._db.conn
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_history (
                analysis_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                source TEXT NOT NULL,
                mode TEXT NOT NULL,
                target_url TEXT,
                request_text TEXT NOT NULL,
                response_text TEXT,
                metadata_json TEXT NOT NULL,
                summary TEXT NOT NULL,
                findings_json TEXT NOT NULL,
                redaction_applied INTEGER NOT NULL,
                llm_status TEXT NOT NULL,
                top_severity TEXT
            )
            """
        )
        # Migration: add top_severity column if missing (existing DBs)
        try:
            conn.execute("SELECT top_severity FROM analysis_history LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE analysis_history ADD COLUMN top_severity TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS endpoints (
                analysis_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                host TEXT,
                method TEXT NOT NULL,
                path_template TEXT NOT NULL,
                param_names TEXT NOT NULL,
                content_type TEXT,
                has_cookie INTEGER NOT NULL DEFAULT 0,
                has_auth_header INTEGER NOT NULL DEFAULT 0
            )
            """
        )

    def _row_to_item(self, row: sqlite3.Row) -> AnalysisHistoryItem:
        return AnalysisHistoryItem(
            analysis_id=row["analysis_id"],
            created_at=row["created_at"],
            source=Source(row["source"]),
            mode=AnalysisMode(row["mode"]),
            target_url=row["target_url"],
            request_text=row["request_text"],
            response_text=row["response_text"],
            metadata=AnalysisMetadata.model_validate_json(row["metadata_json"]),
            summary=row["summary"],
            findings=[Finding.model_validate(item) for item in json.loads(row["findings_json"])],
            redaction_applied=bool(row["redaction_applied"]),
            llm_status=row["llm_status"],
        )

