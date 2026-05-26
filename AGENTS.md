# Agent Instructions

This repository is a local-first Burp AI HTTP Traffic Analyzer. Follow these instructions when acting as an AI coding agent in this project.

## Project boundaries

- Keep raw HTTP traffic, provider API keys, backend tokens, cookies, authorization headers, and session data out of commits, logs, fixtures, screenshots, and generated docs.
- Keep the Burp extension as a thin client. Redaction, LLM provider calls, result parsing, and persistence belong in the FastAPI backend.
- Add or update tests for behavior changes.
- Do not add passive scanner integration without a separate design/review pass.

## Burp extension JAR workflow

The Burp extension JAR is built by GitHub Actions, not manually stored in the repository.

- Workflow file: `.github/workflows/ci.yml`
- Trigger: push or pull request against `main`
- Job: `burp-extension`
- Build command in CI: `cd burp-extension && mvn test package`
- Uploaded artifact name: `burp-ai-extension-jar`
- Artifact path in CI: `burp-extension/target/burp-ai-extension-*.jar`
- Artifact retention: 14 days

When extension code changes are ready, commit and push them to `main`, wait for the CI workflow to pass, then download the `burp-ai-extension-jar` artifact from the latest GitHub Actions run and load that JAR into Burp Suite.

Do not commit generated JAR files. If local Maven is unavailable, use GitHub Actions as the source of the extension JAR.

## Local verification commands

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm test -- --run
npm run build
```

Burp extension, if Maven is installed locally:

```bash
cd burp-extension
mvn test package
```

If Maven is not installed locally, at minimum perform targeted Java checks where possible and rely on the GitHub Actions `burp-extension` job for full test/package verification.
