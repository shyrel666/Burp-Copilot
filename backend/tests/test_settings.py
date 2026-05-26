from app.services.settings_store import SettingsStore


def test_provider_api_key_is_write_only(tmp_path):
    store = SettingsStore(tmp_path)

    store.update_provider(provider="openai", model="gpt-test", api_key="sk-test-key-abcd")
    public_settings = store.get_public_settings()

    assert public_settings.provider == "openai"
    assert public_settings.model == "gpt-test"
    assert public_settings.has_api_key is True
    assert public_settings.masked_api_key == "sk-...abcd"
    assert "sk-test-key-abcd" not in public_settings.model_dump_json()


def test_ollama_provider_has_no_api_key(tmp_path):
    store = SettingsStore(tmp_path)

    store.update_provider(provider="ollama", model="llama3", api_key=None, base_url="http://localhost:11434")
    public_settings = store.get_public_settings()

    assert public_settings.provider == "ollama"
    assert public_settings.model == "llama3"
    assert public_settings.has_api_key is False
    assert public_settings.masked_api_key is None
    assert public_settings.base_url == "http://localhost:11434"


def test_ollama_get_api_key_returns_none(tmp_path):
    store = SettingsStore(tmp_path)

    store.update_provider(provider="openai", model="gpt-test", api_key="sk-test-key-abcd")
    assert store.get_api_key() == "sk-test-key-abcd"

    store.update_provider(provider="ollama", model="llama3", api_key=None)
    assert store.get_api_key() is None


def test_switching_to_ollama_clears_api_key_from_disk(tmp_path):
    store = SettingsStore(tmp_path)

    store.update_provider(provider="openai", model="gpt-test", api_key="sk-test-key-abcd")
    assert store.get_api_key() == "sk-test-key-abcd"

    store.update_provider(provider="ollama", model="llama3", api_key=None)
    assert store.get_api_key() is None

    raw = store._read_raw()
    assert raw.get("api_key", "") == ""


def test_ollama_default_model_is_llama3(tmp_path, monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    store = SettingsStore(tmp_path)

    store.update_provider(provider="ollama", model="llama3")
    public_settings = store.get_public_settings()

    assert public_settings.model == "llama3"


def test_llm_provider_ollama_env_var_uses_ollama_model_default(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    store = SettingsStore(tmp_path)

    public_settings = store.get_public_settings()

    assert public_settings.provider == "ollama"
    assert public_settings.model == "llama3"
    assert public_settings.has_api_key is False
