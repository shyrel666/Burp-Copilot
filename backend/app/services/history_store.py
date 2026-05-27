from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.models.schemas import (
    AnalysisHistoryItem,
    AnalysisMetadata,
    AnalysisMode,
    AnalysisResponse,
    Finding,
    Severity,
    Source,
)


class HistoryStore:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "analysis.sqlite3"
        self._init_db()

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
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO analysis_history (
                    analysis_id, created_at, source, mode, target_url, request_text,
                    response_text, metadata_json, summary, findings_json,
                    redaction_applied, llm_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis.analysis_id,
                    datetime.now(timezone.utc).isoformat(),
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
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        items = [self._row_to_item(row) for row in rows]
        if min_severity:
            items = self._filter_by_severity(items, min_severity)
        return items

    def _filter_by_severity(self, items: list[AnalysisHistoryItem], min_severity: str) -> list[AnalysisHistoryItem]:
        severity_order = [s.value for s in Severity]
        min_index = severity_order.index(min_severity) if min_severity in severity_order else len(severity_order)
        return [
            item for item in items
            if any(
                severity_order.index(f.severity.value) <= min_index
                for f in item.findings
            )
        ]

    def get(self, analysis_id: str) -> AnalysisHistoryItem | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM analysis_history WHERE analysis_id = ?",
                (analysis_id,),
            ).fetchone()
        return self._row_to_item(row) if row else None

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
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
                    llm_status TEXT NOT NULL
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

