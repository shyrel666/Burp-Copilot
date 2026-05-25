from app.services.settings_store import SettingsStore


def test_provider_api_key_is_write_only(tmp_path):
    store = SettingsStore(tmp_path)

    store.update_provider(provider="openai", model="gpt-test", api_key="sk-real-secret-abcd")
    public_settings = store.get_public_settings()

    assert public_settings.provider == "openai"
    assert public_settings.model == "gpt-test"
    assert public_settings.has_api_key is True
    assert public_settings.masked_api_key == "sk-...abcd"
    assert "sk-real-secret-abcd" not in public_settings.model_dump_json()
