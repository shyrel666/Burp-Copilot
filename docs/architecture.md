# Architecture

The MVP is intentionally local-first and single-user.

```text
Burp Suite -> Java Montoya extension -> FastAPI backend -> redaction/input guard
                                                        -> provider registry
                                                           -> cloud LLM provider
                                                           -> local Ollama provider
                                                        -> SQLite history
Dashboard -> REST/SSE -----------------------------------^
```

## Trust Boundary

The backend is the privacy boundary. Burp and the dashboard may submit raw text to localhost, but only redacted text may be sent to an external LLM provider or persisted to SQLite. Direct SSE streaming is allowed for a single in-flight analysis, but streamed events must expose only redacted prompts/results and structured status.

## MVP Non-Goals

- No passive scanner integration.
- No multi-user auth.
- No Redis/Celery queues without a separate design/review pass.
- No WebSocket streaming.
- No raw traffic archive.
