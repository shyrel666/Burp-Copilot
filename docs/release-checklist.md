# v0.1.0 MVP Release Checklist

- Run backend tests: `cd backend && pytest`.
- Run frontend tests: `cd frontend && npm test -- --run`.
- Run frontend build: `cd frontend && npm run build`.
- Run Burp extension build in an environment with Maven and JDK 17+: `cd burp-extension && mvn test package`.
- Confirm the GitHub Actions `burp-extension` job uploads the `burp-ai-extension-jar` artifact.
- Run a secret scan and review any dummy-key false positives.
- Confirm `.env`, SQLite databases, Burp project files, captures, and generated JARs are not tracked.
- Load the generated JAR into Burp and verify both `AI Analyze` and `AI Learn Mode`.
- Tag the first open-source MVP as `v0.1.0-mvp`.
