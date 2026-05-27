from app.models.schemas import AnalysisMode, Source, TaskStatus
from app.services.task_store import TaskStore


def test_enqueue_creates_queued_task(tmp_path):
    store = TaskStore(tmp_path)
    task = store.enqueue(
        source=Source.DASHBOARD,
        mode=AnalysisMode.ANALYZE,
        target_url="https://example.test/api",
        redacted_request="GET /api HTTP/1.1\r\nHost: example.test\r\n\r\n",
        redacted_response="HTTP/1.1 200 OK\r\n\r\nok",
        metadata_json='{"content_encoding":"utf-8","request_truncated":false,"response_truncated":false,"body_omitted_reason":null}',
    )
    assert task.status == TaskStatus.QUEUED
    assert task.task_id
    assert task.source == Source.DASHBOARD
    assert task.mode == AnalysisMode.ANALYZE


def test_fetch_queued_returns_tasks_in_order(tmp_path):
    store = TaskStore(tmp_path)
    store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req1",
        redacted_response=None, metadata_json="{}",
    )
    store.enqueue(
        source=Source.BURP, mode=AnalysisMode.LEARN,
        target_url=None, redacted_request="req2",
        redacted_response=None, metadata_json="{}",
    )
    tasks = store.fetch_queued(limit=10)
    assert len(tasks) == 2
    assert tasks[0]["redacted_request"] == "req1"
    assert tasks[1]["redacted_request"] == "req2"


def test_mark_running_transitions_state(tmp_path):
    store = TaskStore(tmp_path)
    task = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req",
        redacted_response=None, metadata_json="{}",
    )
    store.mark_running(task.task_id)
    updated = store.get(task.task_id)
    assert updated.status == TaskStatus.RUNNING


def test_mark_done_transitions_state(tmp_path):
    store = TaskStore(tmp_path)
    task = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req",
        redacted_response=None, metadata_json="{}",
    )
    store.mark_running(task.task_id)
    store.mark_done(task.task_id, "analysis-123")
    updated = store.get(task.task_id)
    assert updated.status == TaskStatus.DONE
    assert updated.analysis_id == "analysis-123"


def test_mark_failed_transitions_state(tmp_path):
    store = TaskStore(tmp_path)
    task = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req",
        redacted_response=None, metadata_json="{}",
    )
    store.mark_running(task.task_id)
    store.mark_failed(task.task_id, "provider timeout")
    updated = store.get(task.task_id)
    assert updated.status == TaskStatus.FAILED
    assert updated.error_message == "provider timeout"


def test_cancel_queued_task(tmp_path):
    store = TaskStore(tmp_path)
    task = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req",
        redacted_response=None, metadata_json="{}",
    )
    result = store.cancel(task.task_id)
    assert result is True
    updated = store.get(task.task_id)
    assert updated.status == TaskStatus.CANCELLED


def test_cancel_running_task_sets_flag(tmp_path):
    store = TaskStore(tmp_path)
    task = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req",
        redacted_response=None, metadata_json="{}",
    )
    store.mark_running(task.task_id)
    result = store.cancel(task.task_id)
    assert result is True
    assert store.is_cancel_requested(task.task_id) is True
    # Status remains running until worker checks flag
    assert store.get(task.task_id).status == TaskStatus.RUNNING


def test_cancel_done_task_fails(tmp_path):
    store = TaskStore(tmp_path)
    task = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req",
        redacted_response=None, metadata_json="{}",
    )
    store.mark_running(task.task_id)
    store.mark_done(task.task_id, "analysis-id")
    result = store.cancel(task.task_id)
    assert result is False


def test_recover_running_tasks(tmp_path):
    store = TaskStore(tmp_path)
    task1 = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req1",
        redacted_response=None, metadata_json="{}",
    )
    task2 = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req2",
        redacted_response=None, metadata_json="{}",
    )
    store.mark_running(task1.task_id)
    store.mark_running(task2.task_id)

    recovered = store.recover_running_tasks()
    assert recovered == 2
    assert store.get(task1.task_id).status == TaskStatus.QUEUED
    assert store.get(task2.task_id).status == TaskStatus.QUEUED


def test_list_tasks_with_status_filter(tmp_path):
    store = TaskStore(tmp_path)
    t1 = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req1",
        redacted_response=None, metadata_json="{}",
    )
    t2 = store.enqueue(
        source=Source.DASHBOARD, mode=AnalysisMode.ANALYZE,
        target_url=None, redacted_request="req2",
        redacted_response=None, metadata_json="{}",
    )
    store.mark_running(t2.task_id)

    queued = store.list_tasks(status=TaskStatus.QUEUED)
    assert len(queued) == 1
    assert queued[0].task_id == t1.task_id

    running = store.list_tasks(status=TaskStatus.RUNNING)
    assert len(running) == 1
    assert running[0].task_id == t2.task_id


def test_get_nonexistent_returns_none(tmp_path):
    store = TaskStore(tmp_path)
    assert store.get("nonexistent") is None
