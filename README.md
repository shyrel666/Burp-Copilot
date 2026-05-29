# Burp Copilot

An open-source MVP for authorized HTTP traffic review with Burp Suite, a local FastAPI backend, and a React dashboard.

The tool sends selected HTTP messages to a local backend, redacts sensitive data before any cloud LLM call, and returns structured security findings or beginner-friendly learning notes.

## AI pentest copilot (passive)

Beyond per-request analysis, the tool acts as a beginner-friendly, passive AI pentest copilot that answers "where is the attack surface, what should I test first, and how do I verify each suspicious point by hand":

- Recon analysis mode (`recon`) returns, per request, why a point is suspicious, a test priority, and step-by-step manual verification steps. It never generates or sends attack payloads.
- An endpoint/parameter inventory is derived from all analyzed traffic (independent of findings), forming the structural attack surface.
- Architecture fingerprinting classifies the system type (SPA / MPA / REST / GraphQL / CMS / microservice gateway), auth method, and tech stack from captured traffic.
- An architecture-aware, staged testing roadmap is synthesized by the LLM from the system type, endpoint inventory, and findings summary.
- The React dashboard is the default landing view: security-posture stats, a severity donut, the attack surface ("test first"), the architecture card, the staged roadmap, and a recent-findings timeline.
- The Burp extension can auto-analyze in-scope proxy traffic (glob scope rules, 10/s rate limit) and one-click analyze the whole Site Map, then highlight Proxy History entries by severity once analysis completes.

### Authorized use and accuracy

- For authorized security testing only. You are responsible for staying within the agreed scope.
- The tool is passive: it only analyzes already-captured traffic and never sends test payloads. Active verification is a reserved, not-yet-implemented capability (`POST /api/v1/recon/verify` returns disabled) that would require a separate design/review pass.
- AI output may contain false positives and false negatives. Treat all conclusions as leads that require manual verification.

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
- `.github/workflows/release.yml` - release build, secret scan, OpenAPI export, and release artifacts.

## Privacy Boundaries

- Raw HTTP traffic is only processed in memory.
- The database stores redacted request and response text only.
- Logs must not include raw request bodies, cookies, authorization headers, or API keys.
- Provider API keys are write-only through the API. Settings responses only expose masked key state.
- Do not commit real target traffic, real credentials, `.env` files, SQLite databases, local logs, captures, generated JARs, or Burp project files.

## Local Setup

### Docker Compose

Docker Compose runs the backend and frontend only. Postgres, Redis, Celery, and Ollama are not started by this stack.

```bash
cp .env.example .env
docker compose up --build
```

Open the dashboard at `http://localhost:3000`. The backend listens on `http://localhost:8000`.

If you use Ollama, run Ollama separately and set `LLM_PROVIDER=ollama` plus `OLLAMA_BASE_URL` in `.env`.

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

Build the extension JAR with Maven if available:

```bash
cd burp-extension
mvn test package
```

The release and CI workflows also build the extension JAR. Download the `burp-copilot-extension-jar` or release JAR artifact from GitHub Actions/Releases, then load it in Burp Suite Professional or Community under Extensions.

Generated JAR files are not committed to this repository.

## Configuration

Copy `.env.example` to `.env` for local development and fill in local values.

Never commit `.env` or real provider keys.

If `BACKEND_TOKEN` is set for the backend, clients must send the same value in
the `X-Backend-Token` header:

- Dashboard: set `VITE_BACKEND_TOKEN` before running `npm run dev` or building.
  This token is compiled into the JS bundle and visible to anyone who can load the
  page. It prevents casual access but is not a real security credential.
- Burp extension: enter the token in the `Backend Token` field.

LLM provider configuration:

- OpenAI-compatible cloud provider: set `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL`, and optionally `OPENAI_BASE_URL`.
- Local Ollama: run Ollama separately, set `LLM_PROVIDER=ollama`, `OLLAMA_MODEL`, and `OLLAMA_BASE_URL`.

## API Docs

The OpenAPI export is committed at `docs/openapi.json`.

Regenerate it after API changes:

```bash
cd backend
python scripts/export_openapi.py
```

## Verification

Run the local checks before opening a pull request or tagging a release:

```bash
cd backend
pytest
```

```bash
cd frontend
npm test -- --run
npm run build
```

If Maven is installed:

```bash
cd burp-extension
mvn test package
```

## Release

The first public MVP release tag is `v0.1.0-mvp`.

Before tagging:

- Backend, frontend, and Burp extension CI jobs must pass.
- Secret scan must pass.
- Release artifacts must not include `.env`, SQLite databases, captures, local logs, or Burp project files.
- The generated Burp extension JAR must be loaded manually in Burp and verified with `AI Analyze` and `AI Learn Mode`.

Tag only after those checks pass:

```bash
git tag v0.1.0-mvp
git push origin v0.1.0-mvp
```

The release workflow creates a draft GitHub release with the Burp extension JAR, frontend build archive, and OpenAPI export.

## Authorized Use Only

This project is for defensive security review, education, and authorized penetration testing. Do not use it against systems you do not own or have explicit permission to test.

## License

Apache-2.0. See `LICENSE`.
