from __future__ import annotations

import logging

from app.core.input_guard import guard_payload
from app.core.redaction import redact_pair
from app.llm.base import BaseLLMProvider
from app.llm.result_parser import parse_llm_json
from app.models.schemas import AnalysisResponse, AnalyzeRequest, Finding
from app.services.history_store import HistoryStore
from app.services.prompt_builder import build_prompt


logger = logging.getLogger(__name__)


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

        parsed, llm_status = await self._invoke_provider(system_prompt, user_prompt)

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

    async def _invoke_provider(self, system_prompt: str, user_prompt: str) -> tuple[dict, str]:
        try:
            raw = await self.provider.analyze(system_prompt, user_prompt)
        except Exception as exc:
            logger.warning("provider call failed: %s", type(exc).__name__)
            return _failure_payload(), "failed"

        try:
            return parse_llm_json(raw), "ok"
        except ValueError as parse_error:
            logger.info(
                "provider returned unparseable output, attempting repair: %s",
                type(parse_error).__name__,
            )
            try:
                repaired = await self.provider.repair_json(raw, str(parse_error))
                return parse_llm_json(repaired), "repaired"
            except Exception as exc:
                logger.warning("provider repair failed: %s", type(exc).__name__)
                return _failure_payload(), "failed"


def _failure_payload() -> dict:
    return {
        "summary": "The LLM response could not be parsed into the required schema.",
        "findings": [],
    }

