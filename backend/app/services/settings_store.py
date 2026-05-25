from __future__ import annotations

import json
import os
from pathlib import Path

from app.models.schemas import ProviderSettingsResponse


class SettingsStore:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "settings.json"

    def update_provider(self, provider: str, model: str, api_key: str | None = None) -> ProviderSettingsResponse:
        settings = self._read_raw()
        settings["provider"] = provider
        settings["model"] = model
        if api_key:
            settings["api_key"] = api_key
        self._write_raw(settings)
        return self.get_public_settings()

    def get_public_settings(self) -> ProviderSettingsResponse:
        settings = self._read_raw()
        api_key = settings.get("api_key") or ""
        return ProviderSettingsResponse(
            provider=settings.get("provider", "openai"),
            model=settings.get("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
            has_api_key=bool(api_key),
            masked_api_key=_mask_api_key(api_key) if api_key else None,
        )

    def get_api_key(self) -> str | None:
        return self._read_raw().get("api_key") or os.getenv("OPENAI_API_KEY")

    def _read_raw(self) -> dict[str, str]:
        if not self.path.exists():
            return {
                "provider": os.getenv("LLM_PROVIDER", "openai"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "api_key": os.getenv("OPENAI_API_KEY", ""),
            }
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write_raw(self, settings: dict[str, str]) -> None:
        self.path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def _mask_api_key(api_key: str) -> str:
    suffix = api_key[-4:] if len(api_key) >= 4 else "****"
    if api_key.startswith("sk-"):
        return f"sk-...{suffix}"
    return f"...{suffix}"

