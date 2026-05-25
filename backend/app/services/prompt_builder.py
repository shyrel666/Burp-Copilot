from __future__ import annotations

from app.models.schemas import AnalysisMode


ANALYZE_SYSTEM_PROMPT = """You are a web application security reviewer.
Analyze only the supplied HTTP request and response for authorized testing.
Return strict JSON with summary and findings. Do not include markdown."""

LEARN_SYSTEM_PROMPT = """You are a patient security mentor for authorized labs and owner-approved testing.
Explain the security reasoning, evidence, and remediation at a beginner-friendly level.
Avoid autonomous exploitation, persistence, stealth, or bypass instructions.
Return strict JSON with summary and findings. Do not include markdown."""


def build_prompt(mode: AnalysisMode, request_text: str, response_text: str | None, target_url: str | None) -> tuple[str, str]:
    system = LEARN_SYSTEM_PROMPT if mode == AnalysisMode.LEARN else ANALYZE_SYSTEM_PROMPT
    user = "\n".join(
        [
            f"Target URL: {target_url or 'not provided'}",
            "",
            "HTTP request:",
            request_text,
            "",
            "HTTP response:",
            response_text or "not provided",
            "",
            "Required JSON shape:",
            '{"summary":"string","findings":[{"title":"string","severity":"critical|high|medium|low|info",'
            '"confidence":0.0,"evidence":"redacted string","attack_approach":"authorized testing guidance",'
            '"remediation":"string","owasp_category":"optional string"}]}',
        ]
    )
    return system, user

