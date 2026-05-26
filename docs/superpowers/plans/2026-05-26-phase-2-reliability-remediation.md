# Phase 2 Reliability Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining Phase 2 reliability gaps by making provider selection explicit, adding first-class `openai-compatible` support, restoring runnable verification, and adding direct acceptance-test coverage.

**Architecture:** Add a small backend provider registry that maps explicit provider names to provider construction logic, extend settings to persist an optional `base_url`, and route all analyze and health-check calls through the saved settings on every request. Keep the current API surface mostly stable, update the React settings UI to expose explicit provider selection, and prove the Phase 2 acceptance criteria with direct backend and frontend tests.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic v2, httpx, pytest, React, TypeScript, Vitest

---

## File Structure

- Create: `backend/app/llm/provider_registry.py`
  - Own provider-name validation and runtime provider construction.
- Create: `backend/tests/test_provider_registry.py`
  - Direct coverage for supported and unsupported provider names.
- Modify: `backend/app/models/schemas.py:3-5,88-98`
  - Add explicit provider-name type and optional `base_url` to provider settings schemas.
- Modify: `backend/app/services/settings_store.py:16-48`
  - Persist and expose `base_url` alongside provider/model while keeping API keys write-only.
- Modify: `backend/app/main.py:17-74`
  - Replace inline provider construction with registry-backed construction and clear error translation.
- Modify: `backend/tests/test_analysis_api.py:159-252`
  - Add acceptance coverage for runtime provider switching, model switching, and invalid-output fallback.
- Modify: `backend/tests/test_settings.py:4-15`
  - Assert masked keys still hold when `base_url` is present.
- Modify: `frontend/src/types.ts:1-37`
  - Add explicit provider-name union and `base_url` field.
- Modify: `frontend/src/api/client.ts:45-61`
  - Send and receive `base_url` in provider settings calls.
- Modify: `frontend/src/App.tsx:8-13,46-91,187-318`
  - Replace the freeform provider input with explicit options and add a base URL field.
- Modify: `frontend/src/App.test.tsx:24-87`
  - Verify the UI sends explicit provider values and never displays plaintext API keys.

### Task 1: Restore the Verification Baseline

**Files:**
- Modify: none
- Test: `backend/tests/test_openai_provider.py`
- Test: `backend/tests/test_result_parser.py`
- Test: `backend/tests/test_analysis_api.py`
- Test: `backend/tests/test_settings.py`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Install backend runtime and test dependencies**

Run:

```powershell
python -m pip install -e ".[dev]"
```

Expected: backend installs editable package metadata plus `pytest`, `jsonschema`, and other declared dependencies so test collection no longer fails with `ModuleNotFoundError`.

- [ ] **Step 2: Run the backend Phase 2 baseline tests**

Run:

```powershell
python -m pytest tests/test_openai_provider.py tests/test_result_parser.py tests/test_analysis_api.py tests/test_settings.py -v
```

Expected: pytest collects all tests successfully. If failures remain, they should be product-behavior failures, not missing-package failures.

- [ ] **Step 3: Install frontend dependencies**

Run:

```powershell
npm install
```

Expected: `node_modules` is created and `vitest` is available to `npm test`.

- [ ] **Step 4: Run the frontend settings regression test**

Run:

```powershell
npm test -- --run src/App.test.tsx
```

Expected: Vitest starts normally. Any failure should now reflect UI behavior rather than a missing test runner.

- [ ] **Step 5: Record the baseline before code changes**

Create a short working note outside the codebase with:

```text
Backend baseline:
- test_openai_provider: PASS or FAIL
- test_result_parser: PASS or FAIL
- test_analysis_api: PASS or FAIL
- test_settings: PASS or FAIL

Frontend baseline:
- App.test.tsx: PASS or FAIL
```

Expected: you have a before/after verification record for the remediation work.

### Task 2: Add the Backend Provider Contract and Registry

**Files:**
- Create: `backend/app/llm/provider_registry.py`
- Create: `backend/tests/test_provider_registry.py`
- Modify: `backend/app/models/schemas.py:3-5,88-98`
- Modify: `backend/app/services/settings_store.py:16-48`
- Test: `backend/tests/test_settings.py:4-15`

- [ ] **Step 1: Write the failing provider-registry tests**

Create `backend/tests/test_provider_registry.py` with:

```python
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
```

- [ ] **Step 2: Run the new registry tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_provider_registry.py -v
```

Expected: FAIL because `app.llm.provider_registry` does not exist yet.

- [ ] **Step 3: Add the explicit provider type and settings schema fields**

Update `backend/app/models/schemas.py` to add:

```python
class ProviderName(str, Enum):
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai-compatible"


class ProviderSettingsUpdate(BaseModel):
    provider: ProviderName
    model: str = Field(min_length=1)
    api_key: str | None = Field(default=None)
    base_url: str | None = Field(default=None)


class ProviderSettingsResponse(BaseModel):
    provider: ProviderName
    model: str
    has_api_key: bool
    masked_api_key: str | None = None
    base_url: str | None = None
```

- [ ] **Step 4: Implement the provider registry**

Create `backend/app/llm/provider_registry.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass

from app.llm.base import BaseLLMProvider
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

    raise ValueError(f"Unsupported provider: {config.provider}")
```

- [ ] **Step 5: Persist and return `base_url` in the settings store**

Update `backend/app/services/settings_store.py` so the provider update path becomes:

```python
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
    if api_key:
        settings["api_key"] = api_key
    self._write_raw(settings)
    return self.get_public_settings()
```

and the public read path becomes:

```python
def get_public_settings(self) -> ProviderSettingsResponse:
    settings = self._read_raw()
    api_key = settings.get("api_key") or ""
    return ProviderSettingsResponse(
        provider=settings.get("provider", "openai"),
        model=settings.get("model", os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
        has_api_key=bool(api_key),
        masked_api_key=_mask_api_key(api_key) if api_key else None,
        base_url=settings.get("base_url") or None,
    )
```

Also update `_read_raw()` defaults to include:

```python
"base_url": os.getenv("OPENAI_BASE_URL", ""),
```

- [ ] **Step 6: Extend the settings test for masked keys plus `base_url`**

Update `backend/tests/test_settings.py` to:

```python
from app.services.settings_store import SettingsStore


def test_provider_api_key_is_write_only(tmp_path):
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
```

- [ ] **Step 7: Run the registry and settings tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_provider_registry.py tests/test_settings.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit the backend contract and registry**

Run:

```powershell
git add backend/app/llm/provider_registry.py backend/app/models/schemas.py backend/app/services/settings_store.py backend/tests/test_provider_registry.py backend/tests/test_settings.py
git commit -m "feat: add provider registry and settings contract"
```

Expected: one commit containing the provider contract and its direct tests.

### Task 3: Route Analyze and Health Checks Through the Registry

**Files:**
- Modify: `backend/app/main.py:17-74`
- Modify: `backend/tests/test_analysis_api.py:159-252`
- Test: `backend/tests/test_analysis_api.py`

- [ ] **Step 1: Write failing acceptance tests for runtime provider selection and invalid-output fallback**

Add the following tests to `backend/tests/test_analysis_api.py`:

```python
from fastapi.testclient import TestClient

from app.llm.base import HealthCheckResult
from app.llm.fake_provider import VALID_RESPONSE
from app.main import create_app


class BrokenJsonProvider:
    async def analyze(self, system_prompt, user_prompt):
        return "not json"

    async def repair_json(self, invalid_text, error):
        return "still not json"

    async def health_check(self):
        return HealthCheckResult(ok=True, reason="ok")


class CapturingProvider:
    def __init__(self):
        self.calls = []

    async def analyze(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return VALID_RESPONSE

    async def repair_json(self, invalid_text, error):
        return VALID_RESPONSE

    async def health_check(self):
        return HealthCheckResult(ok=True, reason="ok")


def test_saved_provider_model_and_base_url_are_used_without_restart(tmp_path, monkeypatch):
    seen = []
    provider = CapturingProvider()

    def fake_build_provider(config):
        seen.append(config)
        return provider

    monkeypatch.setattr("app.main.build_provider", fake_build_provider)
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    saved = client.put(
        "/api/v1/settings/provider",
        json={
            "provider": "openai-compatible",
            "model": "gpt-compat",
            "api_key": "sk-test-key-4444",
            "base_url": "http://127.0.0.1:11434/v1",
        },
    )
    assert saved.status_code == 200

    response = client.post(
        "/api/v1/analyze",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    )

    assert response.status_code == 200
    assert response.json()["llm_status"] == "ok"
    assert seen[-1].provider == "openai-compatible"
    assert seen[-1].model == "gpt-compat"
    assert seen[-1].base_url == "http://127.0.0.1:11434/v1"


def test_invalid_provider_output_returns_failed_status_when_repair_also_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.build_provider", lambda config: BrokenJsonProvider())
    app = create_app(data_dir=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/v1/analyze",
        json={
            "source": "dashboard",
            "mode": "analyze",
            "request_text": "GET / HTTP/1.1\r\nHost: example.test\r\n\r\n",
            "metadata": {"content_encoding": "utf-8"},
        },
    )

    assert response.status_code == 200
    assert response.json()["llm_status"] == "failed"
    history = client.get("/api/v1/history").json()
    assert history[0]["llm_status"] == "failed"
```

- [ ] **Step 2: Run the focused API tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_analysis_api.py::test_saved_provider_model_and_base_url_are_used_without_restart tests/test_analysis_api.py::test_invalid_provider_output_returns_failed_status_when_repair_also_fails -v
```

Expected: FAIL because `main.py` still builds providers inline and does not pass the new settings contract through the registry.

- [ ] **Step 3: Replace inline provider construction with registry-backed construction**

Update `backend/app/main.py` so the provider construction path becomes:

```python
from app.llm.provider_registry import ProviderConfig, build_provider


@app.put("/api/v1/settings/provider", response_model=ProviderSettingsResponse, dependencies=[require_token])
async def update_provider(update: ProviderSettingsUpdate):
    public = settings.update_provider(update.provider, update.model, update.api_key, update.base_url)
    return public


@app.post("/api/v1/settings/test-provider", dependencies=[require_token])
async def test_provider() -> dict[str, str | bool]:
    try:
        provider = _build_provider(settings, provider_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = await provider.health_check()
    return {"ok": result.ok, "reason": result.reason}


def _build_provider(settings: SettingsStore, provider_mode: str | None):
    if provider_mode == "fake":
        return FakeLLMProvider()
    if provider_mode == "fake-invalid-once":
        return FakeLLMProvider(invalid_once=True)
    public = settings.get_public_settings()
    return build_provider(
        ProviderConfig(
            provider=str(public.provider),
            model=public.model,
            api_key=settings.get_api_key(),
            base_url=public.base_url,
        )
    )
```

Also wrap the `/api/v1/analyze` route provider resolution with the same `ValueError` to `HTTPException(status_code=400)` translation before constructing `AnalysisService`.

- [ ] **Step 4: Run the focused API tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_analysis_api.py::test_saved_provider_model_and_base_url_are_used_without_restart tests/test_analysis_api.py::test_invalid_provider_output_returns_failed_status_when_repair_also_fails -v
```

Expected: PASS.

- [ ] **Step 5: Run the full backend API test file**

Run:

```powershell
python -m pytest tests/test_analysis_api.py -v
```

Expected: PASS, including the existing secret-redaction and provider-health assertions.

- [ ] **Step 6: Commit the backend route integration**

Run:

```powershell
git add backend/app/main.py backend/tests/test_analysis_api.py
git commit -m "feat: route provider settings through registry"
```

Expected: one commit containing the analyze/health-check integration and acceptance tests.

### Task 4: Update the Frontend Settings Contract and UI

**Files:**
- Modify: `frontend/src/types.ts:1-37`
- Modify: `frontend/src/api/client.ts:45-61`
- Modify: `frontend/src/App.tsx:8-13,46-91,187-318`
- Modify: `frontend/src/App.test.tsx:24-87`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing frontend regression test for explicit provider settings**

Update `frontend/src/App.test.tsx` with:

```tsx
test('settings page saves provider, model, and base url without showing the plain api key', async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith('/api/v1/analyze') && init?.method === 'POST') {
      return jsonResponse(analysisResponse);
    }
    if (url.endsWith('/api/v1/history')) {
      return jsonResponse([]);
    }
    if (url.endsWith('/api/v1/settings') && !init?.method) {
      return jsonResponse({
        provider: 'openai',
        model: 'gpt-4o-mini',
        has_api_key: true,
        masked_api_key: 'sk-...1234',
        base_url: null,
      });
    }
    if (url.endsWith('/api/v1/settings/provider')) {
      expect(JSON.parse(String(init?.body))).toEqual({
        provider: 'openai-compatible',
        model: 'gpt-compat',
        api_key: 'sk-test-key-9999',
        base_url: 'http://127.0.0.1:11434/v1',
      });
      return jsonResponse({
        provider: 'openai-compatible',
        model: 'gpt-compat',
        has_api_key: true,
        masked_api_key: 'sk-...9999',
        base_url: 'http://127.0.0.1:11434/v1',
      });
    }
    throw new Error(`Unhandled request: ${url}`);
  });

  vi.stubGlobal('fetch', fetchMock);
  render(<App />);

  await user.click(screen.getByRole('button', { name: /settings/i }));
  await screen.findByText('sk-...1234');
  await user.selectOptions(screen.getByLabelText(/provider/i), 'openai-compatible');
  await user.clear(screen.getByLabelText(/model/i));
  await user.type(screen.getByLabelText(/model/i), 'gpt-compat');
  await user.type(screen.getByLabelText(/base url/i), 'http://127.0.0.1:11434/v1');
  await user.type(screen.getByLabelText(/api key/i), 'sk-test-key-9999');
  await user.click(screen.getByRole('button', { name: /save provider/i }));

  await waitFor(() => expect(screen.getByText('sk-...9999')).toBeInTheDocument());
  expect(screen.queryByText('sk-test-key-9999')).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend test to verify it fails**

Run:

```powershell
npm test -- --run src/App.test.tsx
```

Expected: FAIL because the current UI does not expose a `base_url` field or submit the updated settings payload.

- [ ] **Step 3: Update the frontend types and API client**

Update `frontend/src/types.ts` to:

```ts
export type Mode = 'analyze' | 'learn';
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type ProviderName = 'openai' | 'openai-compatible';

export interface ProviderSettings {
  provider: ProviderName;
  model: string;
  has_api_key: boolean;
  masked_api_key: string | null;
  base_url: string | null;
}
```

and update `frontend/src/api/client.ts` to:

```ts
export function saveProviderSettings(input: {
  provider: ProviderName;
  model: string;
  apiKey?: string;
  baseUrl?: string;
}): Promise<ProviderSettings> {
  return request<ProviderSettings>('/api/v1/settings/provider', {
    method: 'PUT',
    body: JSON.stringify({
      provider: input.provider,
      model: input.model,
      api_key: input.apiKey || null,
      base_url: input.baseUrl || null,
    }),
  });
}
```

- [ ] **Step 4: Replace the freeform provider input with explicit options and a base URL field**

Update `frontend/src/App.tsx` so the settings state and panel become:

```tsx
const emptySettings: ProviderSettings = {
  provider: 'openai',
  model: 'gpt-4o-mini',
  has_api_key: false,
  masked_api_key: null,
  base_url: null,
};
```

```tsx
async function submitSettings(event: FormEvent) {
  event.preventDefault();
  setLoading(true);
  setError(null);
  try {
    const result = await saveProviderSettings({
      provider: settings.provider,
      model: settings.model,
      apiKey,
      baseUrl: settings.base_url || undefined,
    });
    setSettings(result);
    setApiKey('');
  } catch (exc) {
    setError(errorMessage(exc));
  } finally {
    setLoading(false);
  }
}
```

```tsx
<label>
  Provider
  <select
    value={settings.provider}
    onChange={(event) =>
      setSettings({
        ...settings,
        provider: event.target.value as ProviderSettings['provider'],
      })
    }
  >
    <option value="openai">openai</option>
    <option value="openai-compatible">openai-compatible</option>
  </select>
</label>
<label>
  Model
  <input value={settings.model} onChange={(event) => setSettings({ ...settings, model: event.target.value })} />
</label>
<label>
  Base URL
  <input
    value={settings.base_url ?? ''}
    onChange={(event) => setSettings({ ...settings, base_url: event.target.value || null })}
    placeholder="http://127.0.0.1:11434/v1"
  />
</label>
```

- [ ] **Step 5: Run the frontend regression test to verify it passes**

Run:

```powershell
npm test -- --run src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit the frontend settings changes**

Run:

```powershell
git add frontend/src/types.ts frontend/src/api/client.ts frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: add explicit provider settings UI"
```

Expected: one commit containing the updated frontend settings contract and regression test.

### Task 5: Run Final Phase 2 Verification

**Files:**
- Modify: none
- Test: `backend/tests/test_provider_registry.py`
- Test: `backend/tests/test_openai_provider.py`
- Test: `backend/tests/test_result_parser.py`
- Test: `backend/tests/test_analysis_api.py`
- Test: `backend/tests/test_settings.py`
- Test: `frontend/src/App.test.tsx`
- Check: `NEXT_PHASE_DEVELOPMENT.md:42-57`

- [ ] **Step 1: Run the full backend Phase 2 verification set**

Run:

```powershell
python -m pytest tests/test_provider_registry.py tests/test_openai_provider.py tests/test_result_parser.py tests/test_analysis_api.py tests/test_settings.py -v
```

Expected: PASS.

- [ ] **Step 2: Run the frontend regression set**

Run:

```powershell
npm test -- --run src/App.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Verify each Phase 2 acceptance criterion against the passing tests**

Use this checklist:

```text
[ ] Saving a new provider key/model changes subsequent analyze calls immediately.
[ ] Invalid provider output returns structured llm_status: failed instead of crashing.
[ ] Public settings never include plaintext keys.
[ ] Provider registry explicitly supports openai and openai-compatible.
[ ] Provider health checks use current settings without exposing secrets.
[ ] Parser normalization handles markdown-wrapped JSON.
[ ] Provider errors do not persist raw prompts or secrets.
```

Expected: every item is backed by a passing test or direct code path covered in the verification run.

- [ ] **Step 4: Commit the final verification if any follow-up test fixes were required**

Run:

```powershell
git status
```

Expected: clean working tree. If it is not clean because verification required fixes, commit those fixes before closing the phase.
