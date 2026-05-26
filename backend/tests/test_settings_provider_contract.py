import os

from app.services.settings_store import SettingsStore


def test_provider_settings_include_base_url_without_exposing_api_key(tmp_path):
    store = SettingsStore(tmp_path)

    store.update_provider(
        provider="openai-compatible",
        model="gpt-test",
        api_key="sk-test-key-abcd",
        base_url="http://127.0.0.1:11434/v1",
    )
    public_settings = store.get_public_settings()

    assert public_settings.provider == "openai-compatible"
    assert public_settings.model == "gpt-test"
    assert public_settings.has_api_key is True
    assert public_settings.masked_api_key == "sk-...abcd"
    assert public_settings.base_url == "http://127.0.0.1:11434/v1"
    assert "sk-test-key-abcd" not in public_settings.model_dump_json()


def test_empty_api_key_clears_saved_key_and_returns_none(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = SettingsStore(tmp_path)

    store.update_provider("openai", "gpt-test", api_key="sk-test-key-abcd")
    assert store.get_api_key() == "sk-test-key-abcd"

    store.update_provider("openai", "gpt-test", api_key="")
    assert store.get_api_key() is None
    assert store.get_public_settings().has_api_key is False
