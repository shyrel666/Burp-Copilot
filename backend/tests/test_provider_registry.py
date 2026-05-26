import pytest

from app.llm.openai_provider import OpenAIProvider
from app.llm.provider_registry import ProviderConfig, build_provider


def test_build_provider_returns_openai_provider_for_openai_name():
    provider = build_provider(
        ProviderConfig(provider="openai", model="gpt-4o-mini", api_key="sk-test", base_url=None)
    )

    assert isinstance(provider, OpenAIProvider)
    assert provider.base_url == "https://api.openai.com/v1"


def test_build_provider_returns_openai_provider_for_openai_compatible_name():
    provider = build_provider(
        ProviderConfig(
            provider="openai-compatible",
            model="gpt-compat",
            api_key="sk-test",
            base_url="http://127.0.0.1:11434/v1",
        )
    )

    assert isinstance(provider, OpenAIProvider)
    assert provider.base_url == "http://127.0.0.1:11434/v1"


def test_openai_compatible_requires_base_url():
    with pytest.raises(ValueError, match="base_url"):
        build_provider(
            ProviderConfig(provider="openai-compatible", model="gpt-compat", api_key="sk-test", base_url=None)
        )


def test_build_provider_rejects_unsupported_provider_name():
    with pytest.raises(ValueError, match="Unsupported provider"):
        build_provider(
            ProviderConfig(provider="unsupported", model="gpt-test", api_key="sk-test", base_url=None)
        )
