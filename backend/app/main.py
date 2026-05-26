from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.llm.fake_provider import FakeLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider_registry import ProviderConfig, build_provider
from app.models.schemas import AnalyzeRequest, ProviderSettingsResponse, ProviderSettingsUpdate
from app.services.analysis_service import AnalysisService
from app.services.history_store import HistoryStore
from app.services.settings_store import SettingsStore


def create_app(data_dir: str | Path | None = None, provider_mode: str | None = None) -> FastAPI:
    app = FastAPI(title="Burp AI HTTP Traffic Analyzer", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "X-Backend-Token"],
    )
    resolved_data_dir = Path(data_dir or os.getenv("DATA_DIR", "./data"))
    settings = SettingsStore(resolved_data_dir)
    history = HistoryStore(resolved_data_dir)
    require_token = Depends(_require_backend_token)

    _provider_cache: dict = {}

    def _resolve_provider():
        public = settings.get_public_settings()
        key = settings.get_api_key()
        config = (public.provider.value, public.model, key, public.base_url, provider_mode)
        if _provider_cache.get("config") != config:
            _provider_cache["config"] = config
            _provider_cache["instance"] = _build_provider(settings, provider_mode)
        return _provider_cache["instance"]

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

    @app.get("/api/v1/history", dependencies=[require_token])
    async def list_history():
        return history.list()

    @app.get("/api/v1/analysis/{analysis_id}", dependencies=[require_token])
    async def get_analysis(analysis_id: str):
        item = history.get(analysis_id)
        if item is None:
            raise HTTPException(status_code=404, detail="analysis not found")
        return item

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

    return app


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
