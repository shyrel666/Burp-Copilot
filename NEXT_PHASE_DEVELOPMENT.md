# Next Phase Development Guide

This document is for future AI agents continuing the MVP. Keep changes small, test-first, and privacy-preserving.

## Current MVP Snapshot

- Branch: `feature/burp-ai-mvp`
- Backend: FastAPI, SQLite, redaction, input guards, provider settings, OpenAI-compatible provider.
- Frontend: React + Vite dashboard for manual analysis, history, and provider settings.
- Burp extension: Java Montoya thin client with context menu actions and async backend calls.
- Open-source basics: Apache-2.0, README, SECURITY, CONTRIBUTING, CI, release checklist.

## Non-Negotiable Constraints

- Do not persist raw HTTP traffic. Store redacted request/response text only.
- Do not log raw request bodies, cookies, authorization headers, provider keys, or session tokens.
- Keep provider API keys write-only through public APIs. Never return plaintext keys.
- Keep Burp as a thin client. Redaction, LLM calls, and persistence belong in the backend.
- Keep learning mode bounded to authorized testing, explanation, validation thinking, and remediation.
- Do not add passive scanner integration without a separate design/review pass.

## Local Verification Commands

```bash
cd backend
pytest
```

```bash
cd frontend
npm test -- --run
npm run build
```

```bash
cd burp-extension
mvn test package
```

The Burp extension requires Maven and JDK 17 or newer. A JDK 8-only machine can compile only the core helper classes, not the Montoya integration.

## Phase 2: Provider Reliability

Goal: Make cloud provider usage stable enough for real local use.

- Add provider registry with explicit provider names: `openai`, `openai-compatible`, later `anthropic`.
- Add provider health endpoint that uses the current settings and reports actionable failure reasons without exposing secrets.
- Add retry policy for transient provider failures with bounded attempts and timeouts.
- Add response normalization for model outputs that wrap JSON in markdown.
- Add tests proving settings changes take effect without backend restart.
- Add tests proving provider errors do not persist raw prompts or secrets.

Acceptance:

- Saving a new provider key/model changes subsequent analyze calls immediately.
- Invalid provider output returns structured `llm_status: failed` instead of crashing.
- Public settings never include plaintext keys.

## Phase 3: Streaming Analysis

Goal: Add real-time dashboard feedback without introducing Celery yet.

- Add FastAPI SSE endpoint for direct single analysis streaming.
- Keep non-streaming `/api/v1/analyze` as the stable Burp-compatible endpoint.
- Stream status events first: `redacting`, `calling_provider`, `parsing`, `persisted`, `failed`.
- Only stream redacted prompts/results.
- Add frontend streaming result panel.

Acceptance:

- Dashboard shows progress for slow LLM calls.
- Burp extension remains compatible with the non-streaming endpoint.
- Stream failures produce visible UI errors and no raw traffic logs.

## Phase 4: Local Model Support

Goal: Add Ollama as a privacy-first alternative.

- Add `ollama` provider with configurable base URL and model.
- Add provider-specific timeout defaults.
- Add docs for running Ollama locally.
- Add tests with a fake Ollama transport; do not require Ollama in CI.

Acceptance:

- Users can switch provider to Ollama through settings.
- No cloud key is required for Ollama mode.
- Analyze/learn outputs use the same schema as cloud providers.

## Phase 5: Batch And Queue Work

Goal: Support longer-running or multiple-message analyses.

- Add Redis/Celery only after single-message streaming is stable.
- Add task status model: `queued`, `running`, `done`, `failed`, `cancelled`.
- Add cancellation support.
- Add history filters by mode, severity, target host, and time.

Acceptance:

- Batch jobs do not block API workers.
- Queue payloads contain redacted traffic only.
- Failed jobs retain structured error state.

## Phase 6: Burp Extension Hardening

Goal: Improve the Burp user workflow while preserving thin-client boundaries.

- Persist extension settings using Montoya persistence APIs if available.
- Render structured findings instead of raw JSON.
- Add explicit timeout and cancellation UI.
- Add tests for JSON request construction, truncation, and error message formatting.
- Add manual test checklist for Burp Proxy, Repeater, and message editor contexts.

Acceptance:

- Users can restart Burp without retyping backend URL/token.
- Backend unavailable, 401, timeout, and malformed response states are readable.
- No passive scanner hooks are added in this phase.

## Phase 7: Packaging And Release

Goal: Prepare a public GitHub release.

- Add Docker Compose for backend + frontend only; keep Postgres/Ollama optional.
- Add GitHub release workflow that uploads the Burp extension JAR.
- Add generated API docs or OpenAPI export.
- Run a secret scan before tagging.
- Tag the release as `v0.1.0-mvp` only after CI and manual Burp loading pass.

Acceptance:

- A new user can follow README setup without hidden steps.
- Release artifacts contain no `.env`, SQLite DBs, captures, or local logs.
- GitHub Actions build backend, frontend, and Burp extension successfully.

## Suggested First Follow-Up Issue

Title: Enforce backend token in all local clients and document setup

Status: mostly implemented in current branch. Before merging, verify:

- `BACKEND_TOKEN` protects analyze, history, settings, and provider test endpoints.
- `VITE_BACKEND_TOKEN` is sent by the dashboard when configured.
- Burp extension users can enter the same token in the suite tab.
- Health and CORS preflight remain unauthenticated.
