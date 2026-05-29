from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from app.llm.base import BaseLLMProvider
from app.llm.result_parser import parse_llm_json
from app.models.schemas import (
    AnalysisMetadata,
    AnalysisMode,
    AnalysisResponse,
    Finding,
    Source,
)
from app.services.history_store import HistoryStore
from app.services.prompt_builder import build_prompt
from app.services.task_store import TaskStore


logger = logging.getLogger(__name__)


class TaskWorker:
    def __init__(
        self,
        task_store: TaskStore,
        history_store: HistoryStore,
        provider_factory: Callable[[], BaseLLMProvider],
        concurrency: int = 2,
        poll_interval: float = 1.0,
        max_poll_interval: float = 5.0,
    ):
        self.task_store = task_store
        self.history_store = history_store
        self.provider_factory = provider_factory
        self.concurrency = concurrency
        self.poll_interval = poll_interval
        self.max_poll_interval = max_poll_interval
        self._semaphore = asyncio.Semaphore(concurrency)
        self._shutdown = False
        self._task: asyncio.Task | None = None
        self._current_interval = poll_interval
        self._wake_event = asyncio.Event()

    async def start(self) -> None:
        recovered = self.task_store.recover_running_tasks()
        if recovered:
            logger.info("recovered %d stuck tasks back to queued", recovered)
        self._shutdown = False
        self._task = asyncio.create_task(self._run())

    async def stop(self, timeout: float = 5.0) -> None:
        self._shutdown = True
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            self._task = None

    def notify(self) -> None:
        """Wake up the worker immediately (e.g. after enqueueing a task)."""
        self._wake_event.set()

    @property
    def is_running(self) -> bool:
        """True while the worker loop is active (not shutting down)."""
        return not self._shutdown

    async def _run(self) -> None:
        while not self._shutdown:
            tasks = self.task_store.fetch_queued(limit=self.concurrency)
            if tasks:
                self._current_interval = self.poll_interval
                for task_row in tasks:
                    if self._shutdown:
                        break
                    asyncio.create_task(self._process(task_row))
            else:
                self._current_interval = min(
                    self._current_interval * 1.5, self.max_poll_interval
                )
            self._wake_event.clear()
            try:
                await asyncio.wait_for(self._wake_event.wait(), timeout=self._current_interval)
            except asyncio.TimeoutError:
                pass

    async def _process(self, task_row: dict) -> None:
        task_id = task_row["task_id"]
        async with self._semaphore:
            if not self.task_store.mark_running(task_id):
                return
            try:
                source, mode, target_url, metadata, response = await self._run_analysis(task_row)
                if self.task_store.is_cancel_requested(task_id):
                    self.task_store.mark_cancelled(
                        task_id, "Cancelled by user after provider call completed"
                    )
                else:
                    self.history_store.save(
                        source=source,
                        mode=mode,
                        target_url=target_url,
                        request_text=task_row["redacted_request"],
                        response_text=task_row["redacted_response"],
                        metadata=metadata,
                        analysis=response,
                    )
                    self.task_store.mark_done(task_id, response.analysis_id)
            except Exception as exc:
                logger.warning("task %s failed: %s", task_id, exc)
                self.task_store.mark_failed(task_id, str(exc))

    async def _run_analysis(self, task_row: dict) -> tuple[Source, AnalysisMode, str | None, AnalysisMetadata, AnalysisResponse]:
        mode = AnalysisMode(task_row["mode"])
        source = Source(task_row["source"])
        redacted_request = task_row["redacted_request"]
        redacted_response = task_row["redacted_response"]
        target_url = task_row["target_url"]
        metadata = AnalysisMetadata.model_validate_json(task_row["metadata_json"])

        system_prompt, user_prompt = build_prompt(
            mode, redacted_request, redacted_response, target_url
        )

        analysis_id = self.history_store.create_analysis_id()
        provider = self.provider_factory()
        raw_output = await self._call_provider(provider, system_prompt, user_prompt)

        if raw_output is not None:
            parsed, llm_status = await self._parse_raw(provider, raw_output)
        else:
            parsed, llm_status = _failure_payload(), "failed"

        response = AnalysisResponse(
            analysis_id=analysis_id,
            summary=parsed["summary"],
            findings=[Finding.model_validate(item) for item in parsed.get("findings", [])],
            redaction_applied=True,
            llm_status=llm_status,
        )

        return source, mode, target_url, metadata, response

    async def _call_provider(
        self, provider: BaseLLMProvider, system_prompt: str, user_prompt: str
    ) -> str | None:
        try:
            return await provider.analyze(system_prompt, user_prompt)
        except Exception as exc:
            logger.warning("provider call failed: %s", type(exc).__name__)
            return None

    async def _parse_raw(self, provider: BaseLLMProvider, raw: str) -> tuple[dict, str]:
        try:
            return parse_llm_json(raw), "ok"
        except ValueError as parse_error:
            try:
                repaired = await provider.repair_json(raw, str(parse_error))
                return parse_llm_json(repaired), "repaired"
            except Exception:
                return _failure_payload(), "failed"


def _failure_payload() -> dict:
    return {
        "summary": "The LLM response could not be parsed into the required schema.",
        "findings": [],
    }
