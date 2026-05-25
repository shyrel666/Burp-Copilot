from __future__ import annotations

import json
import re

from jsonschema import Draft202012Validator


RESULT_SCHEMA = {
    "type": "object",
    "required": ["summary", "findings"],
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "title",
                    "severity",
                    "confidence",
                    "evidence",
                    "attack_approach",
                    "remediation",
                ],
                "properties": {
                    "title": {"type": "string"},
                    "severity": {"enum": ["critical", "high", "medium", "low", "info"]},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "evidence": {"type": "string"},
                    "attack_approach": {"type": "string"},
                    "remediation": {"type": "string"},
                    "owasp_category": {"type": ["string", "null"]},
                },
                "additionalProperties": True,
            },
        },
    },
    "additionalProperties": True,
}

VALIDATOR = Draft202012Validator(RESULT_SCHEMA)


def parse_llm_json(text: str) -> dict:
    if text is None or not text.strip():
        raise ValueError("Empty LLM response")
    candidate = _extract_json_object(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    errors = sorted(VALIDATOR.iter_errors(parsed), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.path) or "<root>"
        raise ValueError(f"Schema validation failed at {path}: {first.message}")
    return parsed


def _extract_json_object(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    body = fenced.group(1) if fenced else text
    start = body.find("{")
    end = body.rfind("}")
    if start >= 0 and end > start:
        return body[start : end + 1]
    return body

