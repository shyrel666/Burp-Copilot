# Phase 2 Reliability Remediation Design

**Summary:** This design defines the follow-up work required to make Phase 2 in `NEXT_PHASE_DEVELOPMENT.md` actually shippable by closing the provider registry gap, adding explicit `openai-compatible` support, restoring full verification, and adding direct acceptance-test coverage.

## Context

The current codebase already includes most of the reliability primitives for Phase 2:

- `backend/app/llm/openai_provider.py` implements retries, timeouts, and provider health checks.
- `backend/app/llm/result_parser.py` normalizes markdown-wrapped JSON and validates parsed output.
- `backend/app/services/analysis_service.py` returns structured fallback payloads and avoids leaking secrets in logs.
- `backend/app/services/settings_store.py` persists provider settings while masking public API key output.
- `backend/tests/test_openai_provider.py` and `backend/tests/test_settings.py` already validate part of the behavior.

The main remaining gap is architectural: the saved `provider` setting does not actually control runtime provider dispatch. The current `_build_provider()` path in `backend/app/main.py` always builds `OpenAIProvider` except for fake test modes. Because of that, Phase 2 is not fully complete even though several supporting behaviors already exist.

## Problem Statement

Phase 2 cannot be marked complete until the implementation matches the documented scope in `NEXT_PHASE_DEVELOPMENT.md:42-57`.

The unresolved issues are:

- No explicit provider registry exists.
- `openai-compatible` is named in the spec but not implemented in runtime dispatch.
- Some acceptance paths rely on indirect evidence instead of direct tests.
- Full verification is currently blocked by local environment issues.

## Goals

- Make `provider` a real runtime switch rather than a stored label.
- Add explicit support for `openai` and `openai-compatible` as first-class provider names.
- Preserve current privacy guarantees and failure behavior.
- Restore complete backend and frontend verification for Phase 2 related paths.
- Add direct tests for every acceptance criterion in the Phase 2 document.

## Non-Goals

- Adding `anthropic` in this pass.
- Adding new UI concepts beyond what is necessary to support explicit provider selection.
- Introducing streaming or Phase 3 scope.
- Refactoring unrelated backend or frontend modules.

## Approaches Considered

### Approach A: Minimal inline branching in `main.py`

Add more `if/elif` logic to `_build_provider()` and handle `openai-compatible` directly there.

- Pros:
  - Lowest implementation surface
  - Fastest short-term change
- Cons:
  - Keeps provider selection logic coupled to app bootstrapping
  - Makes future provider additions harder to test and extend
  - Leaves less room for validation and provider metadata

### Approach B: Introduce a small provider registry layer

Create a dedicated provider construction layer that maps explicit provider names to factory logic and validates supported names.

- Pros:
  - Clear ownership for provider selection
  - Easier to test directly
  - Keeps `main.py` thin
  - Scales cleanly to later Phase 4 additions like `ollama`
- Cons:
  - Slightly more code than inline branching

### Approach C: Abstract everything behind a large provider manager

Create a broader orchestration service that owns settings lookup, provider health checks, provider construction, and provider metadata.

- Pros:
  - Centralized ownership
- Cons:
  - More abstraction than Phase 2 needs
  - Higher refactor risk
  - Easy to overbuild relative to current project size

## Recommended Approach

Use **Approach B**.

It closes the current Phase 2 gap without over-engineering. A small provider registry gives the project a clean extension point, reduces risk in `main.py`, and provides a testable place to define what provider names are supported right now.

## Proposed Architecture

### 1. Provider registry

Introduce a dedicated backend module responsible for:

- defining supported provider names
- validating input provider names
- constructing the correct provider instance from current settings

This registry should be the only place that knows how provider names map to provider classes and configuration.

### 2. Provider configuration flow

The settings layer remains the source of truth for:

- `provider`
- `model`
- write-only API key storage

The request path should resolve provider settings fresh for each call, then ask the registry to build the correct provider. This preserves the current no-restart behavior while making `provider` meaningful.

### 3. `openai-compatible` support

`openai-compatible` should be treated as an explicit provider name, not as undocumented behavior hidden inside `openai`.

The implementation may reuse the existing `OpenAIProvider` transport format if that is sufficient, but the registry must still distinguish the provider name and feed the correct configuration into it.

If a distinct base URL is required for `openai-compatible`, that configuration path must be explicitly modeled rather than implicitly hardcoded.

### 4. API behavior

The existing settings and analyze endpoints should keep their overall contract stable.

Expected behavior after remediation:

- saving `provider`, `model`, and optional `api_key` affects subsequent analyze calls immediately
- invalid provider names are rejected clearly
- provider health checks run against the currently selected provider
- public settings never expose plaintext secrets

### 5. Test strategy

The remediation is not complete until direct test coverage exists for:

- runtime provider selection by saved `provider`
- `model` changes taking effect without restart
- invalid provider output returning structured `llm_status: failed` when repair also fails
- existing privacy protections continuing to hold
- full parser coverage executing in a working backend environment
- frontend settings flow continuing to reflect masked keys and explicit provider values

## Data Flow

### Analyze request

1. Request arrives at `/api/v1/analyze`.
2. The backend loads current settings from `SettingsStore`.
3. The provider registry validates and constructs the selected provider.
4. `AnalysisService` performs guard + redaction + prompt construction.
5. The selected provider executes the analysis call.
6. The result parser normalizes and validates output.
7. The service returns structured output with `llm_status` and stores only redacted content.

### Provider health check

1. Request arrives at `/api/v1/settings/test-provider`.
2. The backend loads current settings.
3. The provider registry constructs the selected provider.
4. The provider-specific `health_check()` executes.
5. The API returns actionable reasons without exposing secrets.

## Error Handling

- Unsupported provider names should fail fast with a clear validation path.
- Provider outages must continue to return structured fallback analysis results where appropriate.
- Repair failures after invalid model output must continue to degrade to `llm_status: failed` instead of crashing.
- Logging must continue to exclude raw requests, responses, API keys, and tokens.

## Verification Plan

### Environment recovery

Before claiming Phase 2 complete, restore the local verification path:

- backend must have runtime and test dependencies available, including `jsonschema`
- frontend must have test tooling available, including `vitest`

### Required verification commands

Backend target set:

```bash
python -m pytest tests/test_openai_provider.py tests/test_result_parser.py tests/test_analysis_api.py tests/test_settings.py
```

Frontend target set:

```bash
npm test -- --run src/App.test.tsx
```

## Milestones

### Milestone 1: Restore verification baseline

Unblock local backend and frontend test execution so failures reflect product behavior instead of environment issues.

### Milestone 2: Add provider registry

Make runtime provider construction explicit and testable.

### Milestone 3: Add `openai-compatible`

Deliver real support for the documented provider name.

### Milestone 4: Add missing direct acceptance tests

Close the evidence gap around provider switching, model switching, and invalid-output failure handling.

### Milestone 5: Final Phase 2 verification

Run the complete relevant backend and frontend checks and compare the implementation against the documented acceptance criteria.

## Success Criteria

This remediation is complete when all of the following are true:

- `provider` controls runtime provider selection.
- `openai-compatible` is a real supported provider option.
- saving new provider settings affects subsequent analyze calls immediately.
- invalid provider output that cannot be repaired produces structured `llm_status: failed` behavior.
- public settings never expose plaintext secrets.
- Phase 2 related backend and frontend tests run in a working environment and pass.
