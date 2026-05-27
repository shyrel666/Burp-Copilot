# v0.1.0 MVP Release Checklist

- Run backend tests: `cd backend && pytest`.
- Run frontend tests: `cd frontend && npm test -- --run`.
- Run frontend build: `cd frontend && npm run build`.
- Regenerate OpenAPI after API changes: `cd backend && python scripts/export_openapi.py`.
- Build Docker images: `docker compose build`.
- Run Burp extension build in an environment with Maven and JDK 21+: `cd burp-extension && mvn test package`.
- Confirm the GitHub Actions `burp-extension` job uploads the `burp-ai-extension-jar` artifact.
- Confirm the GitHub Actions `Release` workflow runs backend, frontend, Burp extension, OpenAPI export, and secret scan steps.
- Run a secret scan before tagging and review any dummy-key false positives.
- Confirm release artifacts contain only the Burp extension JAR, frontend build archive, OpenAPI export, and GitHub-generated source archives.
- Confirm `.env`, SQLite databases, Burp project files, captures, local logs, and generated JARs are not tracked.
- Load the generated JAR into Burp and verify both `AI Analyze` and `AI Learn Mode`.
- Tag the first open-source MVP as `v0.1.0-mvp` only after CI, secret scan, and manual Burp loading pass.
