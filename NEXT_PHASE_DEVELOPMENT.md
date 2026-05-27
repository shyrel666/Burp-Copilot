# Next Phase Development Guide

This document is for future AI agents continuing the MVP. Keep changes small, test-first, and privacy-preserving.

Status note: this guide reflects the current `main` branch as of 2026-05-26. Earlier Phase 2 remediation plans in `docs/superpowers/` are historical once their listed behavior exists in code and tests.

## Current MVP Snapshot

- Branch: `main`
- Backend: FastAPI, SQLite, redaction, input guards, provider registry, provider settings, OpenAI/OpenAI-compatible/Ollama providers, and direct SSE streaming for single analyses.
- Frontend: React + Vite dashboard for manual analysis, streaming progress, history, and provider settings.
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

Status: complete; keep stable.

Goal: Make cloud provider usage stable enough for real local use.

- Provider registry exists with explicit provider names: `openai`, `openai-compatible`, and `ollama`.
- Provider health endpoint uses current settings and reports actionable failure reasons without exposing secrets.
- OpenAI-compatible providers use a configured base URL.
- Provider calls use bounded retry and timeout behavior.
- Response parsing normalizes model outputs that wrap JSON in markdown.
- Tests cover no-restart settings changes, invalid provider output, and privacy boundaries.

Acceptance:

- Saving a new provider key/model changes subsequent analyze calls immediately.
- Invalid provider output returns structured `llm_status: failed` instead of crashing.
- Public settings never include plaintext keys.
- Provider errors do not persist raw prompts or secrets.

## Phase 3: Streaming Analysis

Status: core complete; stabilize and keep compatible.

Goal: Add real-time dashboard feedback without introducing Celery.

- FastAPI exposes a direct single-analysis SSE endpoint.
- Non-streaming `/api/v1/analyze` remains the stable Burp-compatible endpoint.
- Status events are: `redacting`, `calling_provider`, `parsing`, `persisted`, `failed`.
- Streaming responses expose only redacted prompts/results.
- Frontend shows streaming progress and visible failure states.

Acceptance:

- Dashboard shows progress for slow LLM calls.
- Burp extension remains compatible with the non-streaming endpoint.
- Stream failures produce visible UI errors and no raw traffic logs.
- Interrupted streams do not leave the UI waiting forever.

## Phase 4: Local Model Support

Status: core complete; document and manually verify common local setups.

Goal: Keep Ollama as a privacy-first alternative.

- `ollama` provider exists with configurable base URL and model.
- Ollama uses provider-specific timeout defaults.
- Ollama setup docs exist.
- Tests use fake transports and do not require Ollama in CI.

Acceptance:

- Users can switch provider to Ollama through settings.
- No cloud key is required for Ollama mode.
- Analyze/learn outputs use the same schema as cloud providers.
- Switching to Ollama clears stored cloud API keys from public/runtime provider use.

## Phase 5: Burp Extension Hardening

Status: core complete; add manual test checklist for Burp Proxy, Repeater, and message editor contexts before release.

Goal: Improve the Burp user workflow while preserving thin-client boundaries.

- Persist extension settings using Montoya persistence APIs if available.
- Render structured findings instead of raw JSON.
- Add explicit timeout and cancellation UI.
- Add tests for JSON request construction, truncation, and error message formatting.
- Add manual test checklist for Burp Proxy, Repeater, and message editor contexts.

Acceptance:

- Users can restart Burp without retyping backend URL/token.
- Backend unavailable, 401, timeout, and malformed response states are readable.
- Extension remains a thin client: no redaction, LLM calls, or persistence of raw traffic in Burp.
- No passive scanner hooks are added in this phase.

## Phase 6: Batch And Queue Work

Status: design complete; implementing.

Design document: `docs/phase6-batch-queue-design.md`

Goal: Support longer-running or multiple-message analyses only after a separate design pass.

Design decisions (see design doc for full rationale):

- In-process asyncio queue with SQLite-backed task state (no Redis/Celery).
- Redaction happens before enqueue; queue payloads store only redacted text.
- Task state schema: `queued → running → done/failed/cancelled`.
- Cancellation: immediate for queued; flag-based for running (checked after provider call).
- New `task_queue` table; existing `analysis_history` unchanged.
- History filtering via query params: mode, min_severity, target_host, since, until, limit, offset.
- Zero new external dependencies.

Acceptance:

- Design is reviewed before adding Redis, Celery, or a task queue dependency.
- Batch jobs do not block API workers.
- Queue payloads contain redacted traffic only.
- Failed and cancelled jobs retain structured error state.

## Phase 7: Packaging And Release

Goal: Prepare a public GitHub release.

- Add Docker Compose for backend + frontend only; keep Postgres/Ollama optional.
- Add GitHub release workflow that publishes release artifacts. CI already builds and uploads the Burp extension JAR for push/pull-request workflows.
- Add generated API docs or OpenAPI export.
- Run a secret scan before tagging.
- Tag the release as `v0.1.0-mvp` only after CI and manual Burp loading pass.

Acceptance:

- A new user can follow README setup without hidden steps.
- Release artifacts contain no `.env`, SQLite DBs, captures, or local logs.
- GitHub Actions build backend, frontend, and Burp extension successfully.

## Suggested First Follow-Up Issue

Title: Phase 7 packaging and release preparation

Status: next recommended work after Phase 6 implementation. Scope:

- Add Docker Compose for backend + frontend.
- Add GitHub release workflow.
- Add OpenAPI export and secret scan.
- Tag `v0.1.0-mvp`.
