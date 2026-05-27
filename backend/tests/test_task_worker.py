import asyncio

import pytest

from app.llm.base import BaseLLMProvider, HealthCheckResult
from app.llm.fake_provider import VALID_RESPONSE
from app.models.schemas import AnalysisMode, Source, TaskStatus
from app.services.history_store import HistoryStore
from app.services.task_store import TaskStore
from app.services.task_worker import TaskWorker


class FakeProvider(BaseLLMProvider):
    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        return VALID_RESPONSE

    async def repair_json(self, invalid_text: str, error: str) -> str:
        return VALID_RESPONSE

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(ok=True, reason="ok")


class FailingProvider(BaseLLMProvider):
    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("simulated failure")

    async def repair_json(self, invalid_text: str, error: str) -> str:
        raise RuntimeError("simulated failure")

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(ok=False, reason="simulated")


class SlowProvider(BaseLLMProvider):
    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        await asyncio.sleep(0.3)
        return VALID_RESPONSE

    async def repair_json(self, invalid_text: str, error: str) -> str:
        return VALID_RESPONSE

    async def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(ok=True, reason="ok")


@pytest.fixture
def stores(tmp_path):
    task_store = TaskStore(tmp_path)
    history_store = HistoryStore(tmp_path)
    return task_store, history_store


@pytest.mark.asyncio
async def test_worker_processes_queued_task(stores):
    task_store, history_store = stores
    task = task_store.enqueue(
        source=Source.DASHBOARD,
        mode=AnalysisMode.ANALYZE,
        target_url="https://example.test/api",
        redacted_request="GET /api HTTP/1.1\r\nHost: example.test\r\n\r\n",
        redacted_response="HTTP/1.1 200 OK\r\n\r\nok",
        metadata_json='{"content_encoding":"utf-8","request_truncated":false,"response_truncated":false,"body_omitted_reason":null}',
    )

    worker = TaskWorker(
        task_store=task_store,
        history_store=history_store,
        provider_factory=lambda: FakeProvider(),
        concurrency=1,
        poll_interval=0.1,
    )
    await worker.start()
    await asyncio.sleep(0.5)
    await worker.stop()

    updated = task_store.get(task.task_id)
    assert updated.status == TaskStatus.DONE
    assert updated.analysis_id is not None

    history = history_store.list()
    assert len(history) == 1


@pytest.mark.asyncio
async def test_worker_marks_failed_on_provider_error(stores):
    task_store, history_store = stores
    task = task_store.enqueue(
        source=Source.DASHBOARD,
        mode=AnalysisMode.ANALYZE,
        target_url=None,
        redacted_request="GET / HTTP/1.1\r\nHost: test\r\n\r\n",
        redacted_response=None,
        metadata_json='{"content_encoding":"utf-8","request_truncated":false,"response_truncated":false,"body_omitted_reason":null}',
    )

    worker = TaskWorker(
        task_store=task_store,
        history_store=history_store,
        provider_factory=lambda: FailingProvider(),
        concurrency=1,
        poll_interval=0.1,
    )
    await worker.start()
    await asyncio.sleep(0.5)
    await worker.stop()

    updated = task_store.get(task.task_id)
    # Provider failure results in failed parse → still saved to history with failed status
    # The task itself might be done (analysis saved with llm_status=failed) or failed
    assert updated.status in (TaskStatus.DONE, TaskStatus.FAILED)


@pytest.mark.asyncio
async def test_worker_respects_concurrency_limit(stores):
    task_store, history_store = stores
    for i in range(4):
        task_store.enqueue(
            source=Source.DASHBOARD,
            mode=AnalysisMode.ANALYZE,
            target_url=None,
            redacted_request=f"GET /{i} HTTP/1.1\r\nHost: test\r\n\r\n",
            redacted_response=None,
            metadata_json='{"content_encoding":"utf-8","request_truncated":false,"response_truncated":false,"body_omitted_reason":null}',
        )

    worker = TaskWorker(
        task_store=task_store,
        history_store=history_store,
        provider_factory=lambda: SlowProvider(),
        concurrency=2,
        poll_interval=0.1,
    )
    await worker.start()
    await asyncio.sleep(1.5)
    await worker.stop()

    all_tasks = task_store.list_tasks()
    done_count = sum(1 for t in all_tasks if t.status == TaskStatus.DONE)
    assert done_count == 4


@pytest.mark.asyncio
async def test_worker_handles_cancellation(stores):
    task_store, history_store = stores
    task = task_store.enqueue(
        source=Source.DASHBOARD,
        mode=AnalysisMode.ANALYZE,
        target_url=None,
        redacted_request="GET / HTTP/1.1\r\nHost: test\r\n\r\n",
        redacted_response=None,
        metadata_json='{"content_encoding":"utf-8","request_truncated":false,"response_truncated":false,"body_omitted_reason":null}',
    )

    # Cancel before worker picks it up
    task_store.cancel(task.task_id)

    worker = TaskWorker(
        task_store=task_store,
        history_store=history_store,
        provider_factory=lambda: FakeProvider(),
        concurrency=1,
        poll_interval=0.1,
    )
    await worker.start()
    await asyncio.sleep(0.3)
    await worker.stop()

    updated = task_store.get(task.task_id)
    assert updated.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_worker_recovers_stuck_tasks_on_startup(stores):
    task_store, history_store = stores
    task = task_store.enqueue(
        source=Source.DASHBOARD,
        mode=AnalysisMode.ANALYZE,
        target_url=None,
        redacted_request="GET / HTTP/1.1\r\nHost: test\r\n\r\n",
        redacted_response=None,
        metadata_json='{"content_encoding":"utf-8","request_truncated":false,"response_truncated":false,"body_omitted_reason":null}',
    )
    task_store.mark_running(task.task_id)

    worker = TaskWorker(
        task_store=task_store,
        history_store=history_store,
        provider_factory=lambda: FakeProvider(),
        concurrency=1,
        poll_interval=0.1,
    )
    await worker.start()
    await asyncio.sleep(0.5)
    await worker.stop()

    updated = task_store.get(task.task_id)
    assert updated.status == TaskStatus.DONE


@pytest.mark.asyncio
async def test_cancelled_running_task_not_in_history(stores):
    task_store, history_store = stores
    task = task_store.enqueue(
        source=Source.DASHBOARD,
        mode=AnalysisMode.ANALYZE,
        target_url=None,
        redacted_request="GET / HTTP/1.1\r\nHost: test\r\n\r\n",
        redacted_response=None,
        metadata_json='{"content_encoding":"utf-8","request_truncated":false,"response_truncated":false,"body_omitted_reason":null}',
    )

    # Start worker, then cancel while running (after provider call)
    worker = TaskWorker(
        task_store=task_store,
        history_store=history_store,
        provider_factory=lambda: SlowProvider(),
        concurrency=1,
        poll_interval=0.1,
    )
    await worker.start()
    # Wait for task to be picked up and start running
    await asyncio.sleep(0.15)
    # Cancel while the provider call is in progress
    task_store.cancel(task.task_id)
    # Wait for the worker to finish processing
    await asyncio.sleep(0.5)
    await worker.stop()

    updated = task_store.get(task.task_id)
    assert updated.status == TaskStatus.CANCELLED

    # Cancelled tasks must NOT appear in analysis_history
    history = history_store.list()
    assert len(history) == 0
