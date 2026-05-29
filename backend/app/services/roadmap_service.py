"""Architecture-aware staged testing roadmap synthesis.

Takes the deterministic signals (architecture profile + attack surface + a
compact findings summary) and asks the LLM to act like an experienced
pentester building a step-by-step plan for a beginner. Only a structured
summary is fed to the model (never full traffic) to keep token usage bounded.
No external requests are made; this is pure synthesis over already-captured,
redacted data.
"""

from __future__ import annotations

import json
import logging

from app.llm.base import BaseLLMProvider
from app.llm.result_parser import _extract_json_object
from app.models.schemas import (
    RoadmapResponse,
    RoadmapStage,
)
from app.services.fingerprint_service import FingerprintService
from app.services.history_store import HistoryStore
from app.services.prompt_builder import build_roadmap_prompt
from app.services.statistics_service import StatisticsService


logger = logging.getLogger(__name__)

_MAX_FINDINGS_IN_SUMMARY = 15


class RoadmapService:
    def __init__(
        self,
        history: HistoryStore,
        fingerprints: FingerprintService,
        statistics: StatisticsService,
        provider: BaseLLMProvider,
    ):
        self.history = history
        self.fingerprints = fingerprints
        self.statistics = statistics
        self.provider = provider

    async def build(self, host: str) -> RoadmapResponse:
        profile = self.fingerprints.fingerprint(host)
        surface = self.statistics.get_attack_surface(host=host, limit=40)

        if profile.endpoint_count == 0:
            return RoadmapResponse(
                host=host,
                architecture=profile,
                stages=[],
                llm_status="ok",
                notes="暂无该 host 的已捕获流量，请先在 Burp 中浏览/分析目标。",
            )

        findings_summary = self._summarize_findings(host)
        system_prompt, user_prompt = build_roadmap_prompt(profile, surface, findings_summary)

        stages, status = await self._synthesize(system_prompt, user_prompt)
        return RoadmapResponse(
            host=host,
            architecture=profile,
            stages=stages,
            llm_status=status,
            notes="路线图由 AI 基于已捕获流量归纳，仅供参考，所有结论需人工验证、可能存在误报。",
        )

    def _summarize_findings(self, host: str) -> list[str]:
        seen: set[str] = set()
        summary: list[str] = []
        for item in self.history.list(target_host=host, limit=500):
            for finding in item.findings:
                key = f"{finding.severity.value}|{finding.title}|{finding.owasp_category or ''}"
                if key in seen:
                    continue
                seen.add(key)
                category = f"（{finding.owasp_category}）" if finding.owasp_category else ""
                summary.append(f"[{finding.severity.value}] {finding.title}{category}")
                if len(summary) >= _MAX_FINDINGS_IN_SUMMARY:
                    return summary
        return summary

    async def _synthesize(self, system_prompt: str, user_prompt: str) -> tuple[list[RoadmapStage], str]:
        try:
            raw = await self.provider.analyze(system_prompt, user_prompt)
        except Exception as exc:
            logger.warning("roadmap provider call failed: %s", type(exc).__name__)
            return [], "failed"

        try:
            return self._parse_stages(raw), "ok"
        except (ValueError, TypeError) as first_error:
            logger.info("roadmap output unparseable, attempting repair: %s", type(first_error).__name__)
            try:
                repaired = await self.provider.repair_json(raw, str(first_error))
                return self._parse_stages(repaired), "repaired"
            except Exception as exc:
                logger.warning("roadmap repair failed: %s", type(exc).__name__)
                return [], "failed"

    @staticmethod
    def _parse_stages(text: str) -> list[RoadmapStage]:
        if not text or not text.strip():
            raise ValueError("empty roadmap output")
        data = json.loads(_extract_json_object(text))
        if not isinstance(data, dict) or "stages" not in data:
            raise ValueError("missing 'stages' in roadmap output")
        return [RoadmapStage.model_validate(stage) for stage in data["stages"]]
