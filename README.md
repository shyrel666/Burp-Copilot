# Burp AI HTTP Traffic Analyzer

An open-source MVP for authorized HTTP traffic review with Burp Suite, a local FastAPI backend, and a React dashboard.

The tool sends selected HTTP messages to a local backend, redacts sensitive data before any cloud LLM call, and returns structured security findings or beginner-friendly learning notes.

## Status

This repository contains an MVP implementation. It is intended for local, single-user workflows and authorized security testing only.

## Architecture

```text
Burp Montoya extension
  -> FastAPI backend
  -> redaction and input guards
  -> cloud LLM provider
  -> SQLite history
  -> Burp result panel and React dashboard
```

## Components

- `backend/` - FastAPI API, redaction, input guards, LLM provider, SQLite history.
- `burp-extension/` - Java Montoya extension with async backend calls.
- `frontend/` - React + Vite dashboard for manual analysis and history.
- `.github/workflows/ci.yml` - backend, frontend, and Java build checks.

## Privacy Boundaries

- Raw HTTP traffic is only processed in memory.
- The database stores redacted request and response text only.
- Logs must not include raw request bodies, cookies, authorization headers, or API keys.
- Provider API keys are write-only through the API. Settings responses only expose masked key state.
- Do not commit real target traffic, real credentials, `.env` files, or Burp project files.

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Burp Extension

Build the extension JAR with Maven or through GitHub Actions:

```bash
cd burp-extension
mvn test package
```

Load the generated JAR in Burp Suite Professional or Community under Extensions.

## Configuration

Copy `.env.example` to `.env` for local development and fill in local values.

Never commit `.env` or real provider keys.

If `BACKEND_TOKEN` is set for the backend, clients must send the same value in
the `X-Backend-Token` header:

- Dashboard: set `VITE_BACKEND_TOKEN` before running `npm run dev` or building.
- Burp extension: enter the token in the `Backend Token` field.

## Authorized Use Only

This project is for defensive security review, education, and authorized penetration testing. Do not use it against systems you do not own or have explicit permission to test.

## License

Apache-2.0. See `LICENSE`.
