from __future__ import annotations

from app.core.input_guard import guard_payload
from app.core.redaction import redact_pair
from app.llm.base import BaseLLMProvider
from app.llm.result_parser import parse_llm_json
from app.models.schemas import AnalysisResponse, AnalyzeRequest, Finding
from app.services.history_store import HistoryStore
from app.services.prompt_builder import build_prompt


class AnalysisService:
    def __init__(self, history: HistoryStore, provider: BaseLLMProvider):
        self.history = history
        self.provider = provider

    async def analyze(self, request: AnalyzeRequest) -> AnalysisResponse:
        guarded = guard_payload(
            request.request_text,
            request.response_text,
            request.target_url,
            request.metadata,
        )
        redacted_request, redacted_response = redact_pair(guarded.request_text, guarded.response_text)
        system_prompt, user_prompt = build_prompt(
            request.mode,
            redacted_request,
            redacted_response,
            request.target_url,
        )
        analysis_id = self.history.create_analysis_id()

        try:
            raw = await self.provider.analyze(system_prompt, user_prompt)
            parsed = parse_llm_json(raw)
            llm_status = "ok"
        except Exception as exc:
            try:
                repaired = await self.provider.repair_json(raw if "raw" in locals() else "", str(exc))
                parsed = parse_llm_json(repaired)
                llm_status = "repaired"
            except Exception:
                parsed = {
                    "summary": "The LLM response could not be parsed into the required schema.",
                    "findings": [],
                }
                llm_status = "failed"

        response = AnalysisResponse(
            analysis_id=analysis_id,
            summary=parsed["summary"],
            findings=[Finding.model_validate(item) for item in parsed.get("findings", [])],
            redaction_applied=True,
            llm_status=llm_status,
        )
        self.history.save(
            source=request.source,
            mode=request.mode,
            target_url=request.target_url,
            request_text=redacted_request,
            response_text=redacted_response,
            metadata=guarded.metadata,
            analysis=response,
        )
        return response

