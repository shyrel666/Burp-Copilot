from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from app.core.input_guard import guard_payload
from app.core.redaction import redact_pair, redact_url
from app.llm.base import BaseLLMProvider
from app.llm.result_parser import parse_llm_json
from app.models.schemas import AnalysisResponse, AnalyzeRequest, Finding
from app.services.history_store import HistoryStore
from app.services.prompt_builder import build_prompt


logger = logging.getLogger(__name__)

StreamEvent = tuple[str, dict[str, object]]


class AnalysisService:
    def __init__(self, history: HistoryStore, provider: BaseLLMProvider):
        self.history = history
        self.provider = provider

    async def analyze(self, request: AnalyzeRequest) -> AnalysisResponse:
        result = None
        async for event, payload in self.analyze_with_progress(request):
            if event == "result":
                result = AnalysisResponse.model_validate(payload["analysis"])
        if result is None:
            raise RuntimeError("analysis did not produce a result")
        return result

    async def analyze_with_progress(self, request: AnalyzeRequest) -> AsyncIterator[StreamEvent]:
        yield "status", {"status": "redacting"}
        guarded = guard_payload(
            request.request_text,
            request.response_text,
            request.target_url,
            request.metadata,
        )
        redacted_request, redacted_response = redact_pair(guarded.request_text, guarded.response_text)
        redacted_url = redact_url(request.target_url)
        system_prompt, user_prompt = build_prompt(
            request.mode,
            redacted_request,
            redacted_response,
            redacted_url,
        )
        analysis_id = self.history.create_analysis_id()

        yield "status", {"status": "calling_provider"}
        raw_output = await self._call_provider(system_prompt, user_prompt)
        if raw_output is not None:
            yield "status", {"status": "parsing"}
            parsed, llm_status = await self._parse_raw(raw_output)
        else:
            parsed, llm_status = _failure_payload(), "failed"

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
            target_url=redacted_url,
            request_text=redacted_request,
            response_text=redacted_response,
            metadata=guarded.metadata,
            analysis=response,
        )
        yield "status", {"status": "failed" if llm_status == "failed" else "persisted"}
        yield "result", {"analysis": response.model_dump(mode="json")}

    async def _call_provider(self, system_prompt: str, user_prompt: str) -> str | None:
        try:
            return await self.provider.analyze(system_prompt, user_prompt)
        except Exception as exc:
            logger.warning("provider call failed: %s", type(exc).__name__)
            return None

    async def _parse_raw(self, raw: str) -> tuple[dict, str]:
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
