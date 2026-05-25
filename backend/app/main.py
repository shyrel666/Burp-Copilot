from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.llm.fake_provider import FakeLLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.models.schemas import AnalyzeRequest, ProviderSettingsResponse, ProviderSettingsUpdate
from app.services.analysis_service import AnalysisService
from app.services.history_store import HistoryStore
from app.services.settings_store import SettingsStore


def create_app(data_dir: str | Path | None = None, provider_mode: str | None = None) -> FastAPI:
    app = FastAPI(title="Burp AI HTTP Traffic Analyzer", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "X-Backend-Token"],
    )
    resolved_data_dir = Path(data_dir or os.getenv("DATA_DIR", "./data"))
    settings = SettingsStore(resolved_data_dir)
    history = HistoryStore(resolved_data_dir)
    provider = _build_provider(settings, provider_mode)
    service = AnalysisService(history, provider)

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/analyze")
    async def analyze(request: AnalyzeRequest):
        return await service.analyze(request)

    @app.get("/api/v1/history")
    async def list_history():
        return history.list()

    @app.get("/api/v1/analysis/{analysis_id}")
    async def get_analysis(analysis_id: str):
        item = history.get(analysis_id)
        if item is None:
            raise HTTPException(status_code=404, detail="analysis not found")
        return item

    @app.get("/api/v1/settings", response_model=ProviderSettingsResponse)
    async def get_settings():
        return settings.get_public_settings()

    @app.put("/api/v1/settings/provider", response_model=ProviderSettingsResponse)
    async def update_provider(update: ProviderSettingsUpdate):
        public = settings.update_provider(update.provider, update.model, update.api_key)
        return public

    @app.post("/api/v1/settings/test-provider")
    async def test_provider() -> dict[str, bool]:
        return {"ok": await provider.health_check()}

    return app


def _build_provider(settings: SettingsStore, provider_mode: str | None):
    if provider_mode == "fake":
        return FakeLLMProvider()
    if provider_mode == "fake-invalid-once":
        return FakeLLMProvider(invalid_once=True)
    public = settings.get_public_settings()
    return OpenAIProvider(api_key=settings.get_api_key(), model=public.model)


app = create_app()
