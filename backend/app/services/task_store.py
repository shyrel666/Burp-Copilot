from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.models.schemas import AnalysisMode, Source, TaskInfo, TaskStatus


class TaskStore:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "analysis.sqlite3"
        self._init_db()

    def enqueue(
        self,
        *,
        source: Source,
        mode: AnalysisMode,
        target_url: str | None,
        redacted_request: str,
        redacted_response: str | None,
        metadata_json: str,
    ) -> TaskInfo:
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO task_queue (
                    task_id, created_at, updated_at, status, source, mode,
                    target_url, redacted_request, redacted_response, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id, now, now, TaskStatus.QUEUED.value,
                    source.value, mode.value, target_url,
                    redacted_request, redacted_response, metadata_json,
                ),
            )
        return TaskInfo(
            task_id=task_id,
            status=TaskStatus.QUEUED,
            created_at=now,
            updated_at=now,
            source=source,
            mode=mode,
            target_url=target_url,
        )

    def fetch_queued(self, limit: int = 2) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM task_queue WHERE status = ? ORDER BY created_at ASC LIMIT ?",
                (TaskStatus.QUEUED.value, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_running(self, task_id: str) -> bool:
        """Transition task from queued to running. Returns False if task is no longer queued."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE task_queue SET status = ?, updated_at = ? WHERE task_id = ? AND status = ?",
                (TaskStatus.RUNNING.value, now, task_id, TaskStatus.QUEUED.value),
            )
            return cursor.rowcount > 0

    def mark_done(self, task_id: str, analysis_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE task_queue SET status = ?, analysis_id = ?, updated_at = ? WHERE task_id = ?",
                (TaskStatus.DONE.value, analysis_id, now, task_id),
            )

    def mark_failed(self, task_id: str, error_message: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE task_queue SET status = ?, error_message = ?, updated_at = ? WHERE task_id = ?",
                (TaskStatus.FAILED.value, error_message, now, task_id),
            )

    def mark_cancelled(self, task_id: str, error_message: str = "Cancelled by user") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE task_queue SET status = ?, error_message = ?, updated_at = ? WHERE task_id = ?",
                (TaskStatus.CANCELLED.value, error_message, now, task_id),
            )

    def cancel(self, task_id: str) -> bool:
        """Cancel a queued task. Returns True if cancelled, False if not in queued state."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE task_queue SET status = ?, error_message = ?, updated_at = ? "
                "WHERE task_id = ? AND status = ?",
                (TaskStatus.CANCELLED.value, "Cancelled by user", now, task_id, TaskStatus.QUEUED.value),
            )
            if cursor.rowcount > 0:
                return True
            cursor = conn.execute(
                "UPDATE task_queue SET cancel_requested = 1 WHERE task_id = ? AND status = ?",
                (task_id, TaskStatus.RUNNING.value),
            )
            return cursor.rowcount > 0

    def is_cancel_requested(self, task_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT cancel_requested FROM task_queue WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return bool(row and row[0])

    def get(self, task_id: str) -> TaskInfo | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM task_queue WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return self._row_to_info(row) if row else None

    def list_tasks(self, status: TaskStatus | None = None, limit: int = 50) -> list[TaskInfo]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if status:
                rows = conn.execute(
                    "SELECT * FROM task_queue WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM task_queue ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_info(row) for row in rows]

    def recover_running_tasks(self) -> int:
        """Reset tasks stuck in running state (from a crash) back to queued."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE task_queue SET status = ?, updated_at = ? WHERE status = ?",
                (TaskStatus.QUEUED.value, now, TaskStatus.RUNNING.value),
            )
            return cursor.rowcount

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_queue (
                    task_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    source TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    target_url TEXT,
                    redacted_request TEXT NOT NULL,
                    redacted_response TEXT,
                    metadata_json TEXT NOT NULL,
                    analysis_id TEXT,
                    error_message TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_queue_created ON task_queue(created_at)"
            )

    def _row_to_info(self, row: sqlite3.Row) -> TaskInfo:
        return TaskInfo(
            task_id=row["task_id"],
            status=TaskStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            source=Source(row["source"]),
            mode=AnalysisMode(row["mode"]),
            target_url=row["target_url"],
            analysis_id=row["analysis_id"],
            error_message=row["error_message"],
        )
