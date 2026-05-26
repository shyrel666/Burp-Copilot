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

    def update_provider(
        self,
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> ProviderSettingsResponse:
        settings = self._read_raw()
        settings["provider"] = provider
        settings["model"] = model
        settings["base_url"] = (base_url or "").strip()
        if provider == "ollama":
            settings["api_key"] = ""
        elif api_key is not None:
            settings["api_key"] = api_key
        self._write_raw(settings)
        return self.get_public_settings()

    def get_public_settings(self) -> ProviderSettingsResponse:
        settings = self._read_raw()
        provider = settings.get("provider", "openai")
        api_key = settings.get("api_key") or ""
        if provider == "ollama":
            return ProviderSettingsResponse(
                provider=provider,
                model=settings.get("model", os.getenv("OLLAMA_MODEL", "llama3")),
                has_api_key=False,
                masked_api_key=None,
                base_url=settings.get("base_url") or None,
            )
        return ProviderSettingsResponse(
            provider=provider,
            model=settings.get("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
            has_api_key=bool(api_key),
            masked_api_key=_mask_api_key(api_key) if api_key else None,
            base_url=settings.get("base_url") or None,
        )

    def get_api_key(self) -> str | None:
        raw = self._read_raw()
        if raw.get("provider") == "ollama":
            return None
        if "api_key" in raw:
            stored = raw["api_key"]
            return stored if stored else None
        return os.getenv("OPENAI_API_KEY")

    def _read_raw(self) -> dict[str, str]:
        if not self.path.exists():
            provider = os.getenv("LLM_PROVIDER", "openai")
            if provider == "ollama":
                return {
                    "provider": provider,
                    "model": os.getenv("OLLAMA_MODEL", "llama3"),
                    "api_key": "",
                    "base_url": os.getenv("OLLAMA_BASE_URL", ""),
                }
            return {
                "provider": provider,
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": os.getenv("OPENAI_BASE_URL", ""),
            }
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write_raw(self, settings: dict[str, str]) -> None:
        tmp_path = self.path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)


def _mask_api_key(api_key: str) -> str:
    suffix = api_key[-4:] if len(api_key) >= 4 else "****"
    if api_key.startswith("sk-"):
        return f"sk-...{suffix}"
    return f"...{suffix}"

