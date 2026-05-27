# Phase 6: Batch and Queue Design

**Status:** Approved design  
**Date:** 2026-05-27  
**Scope:** Single-user, local-first batch analysis with in-process task queue

---

## Decision Summary

| Question | Decision |
|----------|----------|
| Redis/Celery vs lighter queue? | In-process asyncio queue with SQLite-backed task state |
| Where does redaction happen? | Before enqueue — queue payloads store only redacted text |
| Task state schema? | `queued → running → done/failed/cancelled` |
| Cancellation semantics? | Cancel flag checked before provider call; running tasks finish current LLM call then mark cancelled |
| SQLite migration? | Add `task_queue` table; existing `analysis_history` unchanged |
| History filtering? | Query params: mode, min_severity, target_host (prefix), time range |
| Local setup implications? | Zero new dependencies; no Redis/Celery install |

---

## 1. Queue Architecture: In-Process asyncio Queue

### Rationale

The MVP is single-user and local-first. Adding Redis/Celery introduces:
- External process management (Redis server)
- Deployment complexity (Docker Compose changes, port conflicts)
- Overkill for 1–10 concurrent analyses on localhost

Instead, we use:
- An **asyncio background worker** consuming from an in-memory deque
- A **SQLite `task_queue` table** for durable task state (survives crashes)
- A configurable **concurrency limit** (default: 2 parallel provider calls)

### Worker Lifecycle

```
App startup → TaskWorker starts (asyncio.create_task)
App shutdown → TaskWorker drains or cancels in-flight tasks (graceful timeout: 5s)
```

The worker polls SQLite for tasks in `queued` state, ordered by `created_at`. On startup, any tasks stuck in `running` state (from a previous crash) are reset to `queued`.

### Why Not Celery Later?

If multi-user or distributed deployment becomes a goal, the task state table schema is compatible with a Celery migration: swap the asyncio worker for a Celery task that reads from the same table. The API layer and task state machine remain unchanged.

---

## 2. Redaction Before Enqueue

### Flow

```
POST /api/v1/batch/submit
  → input_guard (validate payload)
  → redact_pair (redact request/response)
  → redact_url (redact target_url)
  → INSERT INTO task_queue (redacted_request, redacted_response, redacted_url, ...)
  → return task_id + status: queued
```

### Privacy Guarantee

The `task_queue` table **never stores raw traffic**. Columns:
- `redacted_request TEXT NOT NULL`
- `redacted_response TEXT`
- `redacted_url TEXT`

The original raw text is discarded after redaction, before the INSERT. This is the same guarantee as the existing synchronous `/api/v1/analyze` endpoint, which also redacts before persisting to `analysis_history`.

### Proof of Compliance

- Unit test: submit batch item → read task_queue row → assert no raw patterns present
- The `task_queue` schema has no `raw_*` columns
- Redaction runs in the HTTP handler, not in the background worker

---

## 3. Task State Schema

### States

```
queued → running → done
                 → failed
       → cancelled (from queued)
running → cancelled (sets cancel flag; task completes current LLM call then writes cancelled)
```

### SQLite Table: `task_queue`

```sql
CREATE TABLE IF NOT EXISTS task_queue (
    task_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',  -- queued | running | done | failed | cancelled
    source TEXT NOT NULL,
    mode TEXT NOT NULL,
    target_url TEXT,
    redacted_request TEXT NOT NULL,
    redacted_response TEXT,
    metadata_json TEXT NOT NULL,
    analysis_id TEXT,           -- set when done; FK to analysis_history
    error_message TEXT,         -- set when failed
    cancel_requested INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_created ON task_queue(created_at);
```

### State Transitions (enforced in code)

| From | To | Trigger |
|------|----|---------|
| queued | running | Worker picks up task |
| queued | cancelled | User cancels before worker picks it up |
| running | done | Analysis completes successfully |
| running | failed | Provider error or parse failure |
| running | cancelled | cancel_requested=1 checked after provider call returns |

---

## 4. Cancellation Semantics

### Queued Tasks

Immediate: UPDATE status='cancelled' WHERE task_id=? AND status='queued'. Returns 200 if rows affected, 409 if task already running/done.

### Running Tasks

- Set `cancel_requested = 1` in the DB.
- The worker checks `cancel_requested` after the provider call returns (we cannot interrupt an in-flight HTTP call to the LLM provider without connection abort).
- If cancel_requested=1 after provider returns, the worker:
  - Does NOT persist to `analysis_history`
  - Sets status='cancelled'
  - Sets `error_message = "Cancelled by user after provider call completed"`

### Done/Failed Tasks

Cannot be cancelled (409 Conflict).

### Persisted History Rows

Cancelled tasks do not appear in `analysis_history`. Only `done` tasks are persisted to history.

---

## 5. SQLite Migration and Compatibility

### Strategy

- The existing `analysis_history` table is **unchanged**.
- A new `task_queue` table is created via `_init_db()` in a new `TaskStore` class.
- Both tables live in the same `analysis.sqlite3` file.
- No ALTER TABLE on existing schema.
- Old databases without `task_queue` get the table created on first access (CREATE IF NOT EXISTS pattern, same as existing code).

### Backward Compatibility

- The synchronous `/api/v1/analyze` endpoint remains unchanged and does NOT use the task queue.
- The streaming `/api/v1/analyze/stream` endpoint remains unchanged.
- Batch is an additive feature via new endpoints.
- Burp extension continues to use `/api/v1/analyze` (non-batch).

---

## 6. History Filtering

### New Query Parameters on `GET /api/v1/history`

| Param | Type | Description |
|-------|------|-------------|
| `mode` | string | Filter by analysis mode: `analyze` or `learn` |
| `min_severity` | string | Minimum finding severity: `critical`, `high`, `medium`, `low`, `info` |
| `target_host` | string | Prefix match on target_url (e.g., `api.example.com`) |
| `since` | string (ISO 8601) | Only results after this timestamp |
| `until` | string (ISO 8601) | Only results before this timestamp |
| `limit` | int | Max results (default 100, max 500) |
| `offset` | int | Pagination offset (default 0) |

### Severity Filtering

Since findings are stored as JSON array, severity filtering requires scanning `findings_json`. For the MVP single-user scale (<10k rows), a Python-side filter after SQL fetch is acceptable. If performance becomes an issue, add a `max_severity TEXT` denormalized column in a future migration.

### Implementation

```python
def list(self, *, mode=None, min_severity=None, target_host=None,
         since=None, until=None, limit=100, offset=0):
    query = "SELECT * FROM analysis_history WHERE 1=1"
    params = []
    if mode:
        query += " AND mode = ?"; params.append(mode)
    if target_host:
        query += " AND target_url LIKE ?"; params.append(f"%{target_host}%")
    if since:
        query += " AND created_at >= ?"; params.append(since)
    if until:
        query += " AND created_at <= ?"; params.append(until)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    # ... execute, then filter by min_severity in Python if needed
```

---

## 7. Local Setup and Release Implications

### Zero New Dependencies

- No Redis, no Celery, no RQ, no new pip packages.
- The asyncio worker uses only stdlib + existing FastAPI/Pydantic.
- SQLite remains the sole persistence layer.

### New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/batch/submit` | Submit one or more items for batch analysis |
| GET | `/api/v1/batch/tasks` | List task queue with status filters |
| GET | `/api/v1/batch/tasks/{task_id}` | Get single task status |
| POST | `/api/v1/batch/tasks/{task_id}/cancel` | Cancel a task |

### Burp Extension Impact

- Burp extension continues to use synchronous `/api/v1/analyze`. No changes needed.
- A future Burp UI enhancement could add "Send to batch" as a context menu option, but that is out of scope for Phase 6.

### Docker / Release

- No new services in Docker Compose.
- No new environment variables required (concurrency limit is optional: `BATCH_CONCURRENCY=2`).
- README update: document batch endpoints and history filtering params.

---

## 8. Batch Submit API Design

### Request

```json
POST /api/v1/batch/submit
{
  "items": [
    {
      "source": "dashboard",
      "mode": "analyze",
      "request_text": "GET /api/users HTTP/1.1\nHost: example.com\n...",
      "response_text": "HTTP/1.1 200 OK\n...",
      "target_url": "https://example.com/api/users",
      "metadata": {}
    }
  ]
}
```

Maximum items per request: 20 (configurable via `BATCH_MAX_ITEMS`).

### Response

```json
{
  "tasks": [
    {"task_id": "uuid-1", "status": "queued", "created_at": "..."},
    {"task_id": "uuid-2", "status": "queued", "created_at": "..."}
  ]
}
```

### Redaction flow per item:
1. `guard_payload()` — validates and sanitizes
2. `redact_pair()` — removes sensitive patterns
3. `redact_url()` — redacts URL credentials
4. INSERT redacted data into `task_queue`

---

## 9. Worker Design

```python
class TaskWorker:
    def __init__(self, task_store, history_store, provider_factory, concurrency=2):
        self.semaphore = asyncio.Semaphore(concurrency)
        ...

    async def run(self):
        """Main loop: poll for queued tasks, process with bounded concurrency."""
        while not self._shutdown:
            tasks = self.task_store.fetch_queued(limit=self.semaphore._value)
            for task in tasks:
                asyncio.create_task(self._process(task))
            await asyncio.sleep(1)  # poll interval

    async def _process(self, task):
        async with self.semaphore:
            self.task_store.mark_running(task.task_id)
            try:
                result = await self._run_analysis(task)
                if self.task_store.is_cancel_requested(task.task_id):
                    self.task_store.mark_cancelled(task.task_id)
                else:
                    # persist to analysis_history
                    self.history_store.save(...)
                    self.task_store.mark_done(task.task_id, result.analysis_id)
            except Exception as e:
                self.task_store.mark_failed(task.task_id, str(e))
```

---

## 10. Test Plan

| Area | Tests |
|------|-------|
| TaskStore | CRUD operations, state transitions, crash recovery (running→queued on startup) |
| TaskWorker | Processes queued tasks, respects concurrency limit, handles cancellation |
| Batch endpoint | Validates input, redacts before storing, returns task IDs |
| Cancel endpoint | Cancels queued task, rejects cancel on done task, sets flag on running |
| History filtering | Each filter param, combined filters, pagination |
| Privacy | Queue payloads contain only redacted text, no raw patterns |

---

## Appendix: File Changes Overview

| File | Change |
|------|--------|
| `backend/app/services/task_store.py` | New — task queue CRUD + state machine |
| `backend/app/services/task_worker.py` | New — asyncio background worker |
| `backend/app/services/history_store.py` | Add filtering params to `list()` |
| `backend/app/models/schemas.py` | Add batch/task schemas |
| `backend/app/main.py` | Add batch endpoints, start/stop worker on lifespan |
| `frontend/src/api/` | Add batch API client |
| `frontend/src/App.tsx` | Add batch submit UI + task status view + history filters |
| `backend/tests/` | New test files for task_store, task_worker, batch API, history filtering |
