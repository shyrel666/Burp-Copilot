# Contributing

Thanks for helping improve Burp AI HTTP Traffic Analyzer.

## Development Rules

- Keep raw traffic and secrets out of commits, fixtures, logs, and screenshots.
- Add or update tests for behavior changes.
- Keep the Burp extension as a thin client. LLM calls and redaction belong in the backend.
- Keep learning-mode output educational and bounded to authorized testing.

## Pull Request Checklist

- Backend tests pass.
- Frontend build passes.
- Burp extension build passes.
- No real credentials or traffic samples are included.
- Public API changes are documented in `README.md`.
