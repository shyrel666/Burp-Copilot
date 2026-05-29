from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.core.input_guard import guard_payload
from app.core.redaction import redact_pair, redact_url
from app.llm.fake_provider import FakeLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider_registry import ProviderConfig, build_provider
from app.models.schemas import (
    AnalyzeRequest,
    ArchitectureProfile,
    AttackSurfaceResponse,
    BatchSubmitRequest,
    BatchSubmitResponse,
    ProviderSettingsResponse,
    ProviderSettingsUpdate,
    RecentFinding,
    RoadmapRequest,
    RoadmapResponse,
    StatisticsResponse,
    TaskInfo,
    TaskStatus,
)
from app.services.analysis_service import AnalysisService
from app.services.fingerprint_service import FingerprintService
from app.services.history_store import HistoryStore
from app.services.roadmap_service import RoadmapService
from app.services.settings_store import SettingsStore
from app.services.statistics_service import StatisticsService
from app.services.task_store import TaskStore
from app.services.task_worker import TaskWorker


def create_app(data_dir: str | Path | None = None, provider_mode: str | None = None) -> FastAPI:
    resolved_data_dir = Path(data_dir or os.getenv("DATA_DIR", "./data"))
    settings = SettingsStore(resolved_data_dir)
    history = HistoryStore(resolved_data_dir)
    task_store = TaskStore(resolved_data_dir)
    statistics = StatisticsService(history)
    fingerprints = FingerprintService(history)

    _provider_cache: dict = {}

    def _resolve_provider():
        public = settings.get_public_settings()
        key = settings.get_api_key()
        config = (public.provider.value, public.model, key, public.base_url, provider_mode)
        if _provider_cache.get("config") != config:
            _provider_cache["config"] = config
            _provider_cache["instance"] = _build_provider(settings, provider_mode)
        return _provider_cache["instance"]

    concurrency = int(os.getenv("BATCH_CONCURRENCY", "2"))
    worker = TaskWorker(
        task_store=task_store,
        history_store=history,
        provider_factory=_resolve_provider,
        concurrency=concurrency,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        await worker.start()
        yield
        await worker.stop()

    app = FastAPI(title="Burp AI HTTP Traffic Analyzer", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "X-Backend-Token"],
    )
    require_token = Depends(_require_backend_token)

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/analyze", dependencies=[require_token])
    async def analyze(request: AnalyzeRequest):
        try:
            provider = _resolve_provider()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        service = AnalysisService(history, provider)
        return await service.analyze(request)

    @app.post("/api/v1/analyze/stream", dependencies=[require_token])
    async def stream_analyze(request: AnalyzeRequest):
        try:
            provider = _resolve_provider()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        service = AnalysisService(history, provider)
        return StreamingResponse(
            _encode_sse(service.analyze_with_progress(request)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    _valid_severities = {"critical", "high", "medium", "low", "info"}

    @app.get("/api/v1/history", dependencies=[require_token])
    async def list_history(
        mode: str | None = Query(default=None),
        min_severity: str | None = Query(default=None),
        target_host: str | None = Query(default=None),
        since: str | None = Query(default=None),
        until: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ):
        if min_severity and min_severity not in _valid_severities:
            raise HTTPException(status_code=422, detail=f"invalid min_severity: must be one of {sorted(_valid_severities)}")
        return history.list(
            mode=mode,
            min_severity=min_severity,
            target_host=target_host,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )

    @app.get("/api/v1/analysis/{analysis_id}", dependencies=[require_token])
    async def get_analysis(analysis_id: str):
        item = history.get(analysis_id)
        if item is None:
            raise HTTPException(status_code=404, detail="analysis not found")
        return item

    @app.get("/api/v1/statistics", response_model=StatisticsResponse, dependencies=[require_token])
    async def get_statistics(since: str | None = Query(default=None)):
        _validate_iso8601(since)
        return statistics.get_statistics(since=since)

    @app.get(
        "/api/v1/statistics/recent-findings",
        response_model=list[RecentFinding],
        dependencies=[require_token],
    )
    async def get_recent_findings(limit: int = Query(default=20, ge=1, le=100)):
        return statistics.get_recent_findings(limit=limit)

    @app.get(
        "/api/v1/statistics/attack-surface",
        response_model=AttackSurfaceResponse,
        dependencies=[require_token],
    )
    async def get_attack_surface(
        host: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
    ):
        return statistics.get_attack_surface(host=host, limit=limit)

    @app.get(
        "/api/v1/recon/architecture",
        response_model=ArchitectureProfile,
        dependencies=[require_token],
    )
    async def get_architecture(host: str = Query(..., min_length=1)):
        return fingerprints.fingerprint(host)

    @app.post(
        "/api/v1/recon/roadmap",
        response_model=RoadmapResponse,
        dependencies=[require_token],
    )
    async def build_roadmap(request: RoadmapRequest):
        try:
            provider = _resolve_provider()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        service = RoadmapService(history, fingerprints, statistics, provider)
        return await service.build(request.host)

    # --- Active verification (reserved seam, intentionally NOT implemented) ---
    # The tool is passive-only: it never crafts or sends attack payloads. This
    # endpoint reserves the contract for a future, separately-reviewed active
    # verification capability that MUST add scope enforcement, rate limiting,
    # an audit trail, and explicit per-target confirmation before sending any
    # request. Until then it always reports "disabled".
    @app.post("/api/v1/recon/verify", dependencies=[require_token])
    async def verify_finding() -> dict[str, object]:
        return {
            "enabled": False,
            "reason": "主动验证未启用：本工具当前为被动分析，不发送任何测试载荷。该能力需单独设计评审后开启。",
        }

    @app.get("/api/v1/settings", response_model=ProviderSettingsResponse, dependencies=[require_token])
    async def get_settings():
        return settings.get_public_settings()

    @app.put("/api/v1/settings/provider", response_model=ProviderSettingsResponse, dependencies=[require_token])
    async def update_provider(update: ProviderSettingsUpdate):
        public = settings.update_provider(update.provider, update.model, update.api_key, update.base_url)
        return public

    @app.post("/api/v1/settings/test-provider", dependencies=[require_token])
    async def test_provider() -> dict[str, str | bool]:
        try:
            provider = _resolve_provider()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result = await provider.health_check()
        return {"ok": result.ok, "reason": result.reason}

    # --- Batch endpoints ---

    batch_max_items = int(os.getenv("BATCH_MAX_ITEMS", "20"))

    @app.post("/api/v1/batch/submit", response_model=BatchSubmitResponse, dependencies=[require_token])
    async def batch_submit(request: BatchSubmitRequest):
        if len(request.items) > batch_max_items:
            raise HTTPException(status_code=422, detail=f"batch exceeds limit of {batch_max_items} items")

        tasks = []
        for item in request.items:
            guarded = guard_payload(
                item.request_text, item.response_text, item.target_url, item.metadata
            )
            redacted_request, redacted_response = redact_pair(guarded.request_text, guarded.response_text)
            redacted_target = redact_url(item.target_url)
            task_info = task_store.enqueue(
                source=item.source,
                mode=item.mode,
                target_url=redacted_target,
                redacted_request=redacted_request,
                redacted_response=redacted_response,
                metadata_json=guarded.metadata.model_dump_json(),
            )
            tasks.append(task_info)
        return BatchSubmitResponse(tasks=tasks)

    @app.get("/api/v1/batch/tasks", response_model=list[TaskInfo], dependencies=[require_token])
    async def list_tasks(status: str | None = Query(default=None)):
        task_status = TaskStatus(status) if status else None
        return task_store.list_tasks(status=task_status)

    @app.get("/api/v1/batch/tasks/{task_id}", response_model=TaskInfo, dependencies=[require_token])
    async def get_task(task_id: str):
        task = task_store.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task not found")
        return task

    @app.post("/api/v1/batch/tasks/{task_id}/cancel", dependencies=[require_token])
    async def cancel_task(task_id: str):
        task = task_store.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task not found")
        if task.status in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED):
            raise HTTPException(status_code=409, detail=f"cannot cancel task in {task.status.value} state")
        success = task_store.cancel(task_id)
        if not success:
            raise HTTPException(status_code=409, detail="task could not be cancelled")
        return {"task_id": task_id, "status": "cancelled"}

    return app


def _validate_iso8601(value: str | None) -> None:
    if value is None:
        return
    from datetime import datetime

    candidate = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="invalid 'since': must be an ISO 8601 timestamp"
        ) from exc


async def _encode_sse(events):
    async for event_name, payload in events:
        yield f"event: {event_name}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def _build_provider(settings: SettingsStore, provider_mode: str | None):
    if provider_mode == "fake":
        return FakeLLMProvider()
    if provider_mode == "fake-invalid-once":
        return FakeLLMProvider(invalid_once=True)
    public = settings.get_public_settings()
    return build_provider(
        ProviderConfig(
            provider=public.provider.value,
            model=public.model,
            api_key=settings.get_api_key(),
            base_url=public.base_url,
        )
    )


def _require_backend_token(x_backend_token: str | None = Header(default=None)) -> None:
    configured_token = os.getenv("BACKEND_TOKEN")
    if configured_token and x_backend_token != configured_token:
        raise HTTPException(status_code=401, detail="invalid backend token")


app = create_app()
