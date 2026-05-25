# Architecture

The MVP is intentionally local-first and single-user.

```text
Burp Suite -> Java Montoya extension -> FastAPI backend -> redaction/input guard
                                                        -> cloud LLM provider
                                                        -> SQLite history
Dashboard ----------------------------------------------^
```

## Trust Boundary

The backend is the privacy boundary. Burp and the dashboard may submit raw text to localhost, but only redacted text may be sent to an external LLM provider or persisted to SQLite.

## MVP Non-Goals

- No passive scanner integration.
- No multi-user auth.
- No Redis/Celery queues.
- No SSE or WebSocket streaming.
- No raw traffic archive.
