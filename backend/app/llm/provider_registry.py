from __future__ import annotations

from dataclasses import dataclass

from app.llm.base import BaseLLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider
from app.models.schemas import ProviderName


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str | None
    base_url: str | None = None


def build_provider(config: ProviderConfig) -> BaseLLMProvider:
    if config.provider == ProviderName.OPENAI.value:
        return OpenAIProvider(api_key=config.api_key, model=config.model)

    if config.provider == ProviderName.OPENAI_COMPATIBLE.value:
        if not config.base_url:
            raise ValueError("openai-compatible provider requires base_url")
        return OpenAIProvider(api_key=config.api_key, model=config.model, base_url=config.base_url)

    if config.provider == ProviderName.DEEPSEEK.value:
        return OpenAIProvider(
            api_key=config.api_key,
            model=config.model or "deepseek-v4-pro",
            base_url="https://api.deepseek.com",
        )

    if config.provider == ProviderName.OLLAMA.value:
        return OllamaProvider(model=config.model, base_url=config.base_url)

    raise ValueError(f"Unsupported provider: {config.provider}")
