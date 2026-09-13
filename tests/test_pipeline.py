"""
src.pipeline.task_queue 单元测试
基于真实 API: Task / TaskStatus / TaskPriority / TaskQueue
注意: TaskQueue 是单例，测试间需重置内部状态避免互相影响。
"""
import time

import pytest

from src.pipeline.task_queue import (
    Task, TaskStatus, TaskPriority, TaskQueue,
)


@pytest.fixture()
def queue():
    """获取单例并重置其内部状态，保证测试隔离"""
    q = TaskQueue()
    q.stop(wait=False)
    with q._task_lock:
        q._history.clear()
        q._active.clear()
        # 清空优先级队列
        while not q._queue.empty():
            try:
                q._queue.get_nowait()
            except Exception:
                break
    q._paused = False
    yield q
    q.stop(wait=False)


class TestTaskDataclass:
    def test_default_id_generated(self):
        t = Task(name="x")
        assert t.id and len(t.id) == 12

    def test_default_status_queued(self):
        assert Task().status == TaskStatus.QUEUED

    def test_default_priority_normal(self):
        assert Task().priority == TaskPriority.NORMAL

    def test_to_dict_keys(self):
        d = Task(name="n", description="d").to_dict()
        for key in ("id", "name", "status", "priority", "progress", "created_at"):
            assert key in d

    def test_to_dict_status_value(self):
        assert Task().to_dict()["status"] == "queued"

    def test_unique_ids(self):
        assert Task().id != Task().id


class TestTaskStatusEnum:
    def test_values(self):
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestTaskPriorityEnum:
    def test_ordering(self):
        assert TaskPriority.CRITICAL.value > TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value > TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value > TaskPriority.LOW.value


class TestSubmit:
    def test_submit_returns_id(self, queue):
        tid = queue.submit(Task(name="t1"))
        assert isinstance(tid, str) and tid

    def test_submit_adds_to_history(self, queue):
        t = Task(name="t2")
        queue.submit(t)
        assert queue.get_task(t.id) is not None

    def test_submit_increases_queue_size(self, queue):
        queue.submit(Task(name="t3"))
        assert queue.get_queue_size() >= 1

    def test_submit_function(self, queue):
        def dummy():
            return 1
        tid = queue.submit_function("job", dummy)
        assert queue.get_task(tid) is not None
        assert queue.get_task(tid).name == "job"

    def test_submit_function_with_priority(self, queue):
        tid = queue.submit_function("hp", lambda: None, priority=TaskPriority.HIGH)
        assert queue.get_task(tid).priority == TaskPriority.HIGH


class TestGetters:
    def test_get_task_missing_returns_none(self, queue):
        assert queue.get_task("nonexistent_id") is None

    def test_get_all_tasks(self, queue):
        queue.submit(Task(name="a"))
        queue.submit(Task(name="b"))
        all_t = queue.get_all_tasks()
        assert len(all_t) >= 2

    def test_get_queued_tasks(self, queue):
        queue.submit(Task(name="q1"))
        queued = queue.get_queued_tasks()
        assert isinstance(queued, list)

    def test_get_active_count_initial_zero(self, queue):
        assert queue.get_active_count() == 0

    def test_get_active_tasks_empty(self, queue):
        assert queue.get_active_tasks() == []


class TestCancel:
    def test_cancel_queued_task(self, queue):
        t = Task(name="cancel_me")
        queue.submit(t)
        ok = queue.cancel(t.id)
        assert ok is True
        assert queue.get_task(t.id).status == TaskStatus.CANCELLED

    def test_cancel_nonexistent_returns_false(self, queue):
        assert queue.cancel("no_such_id") is False


class TestConcurrencyControl:
    def test_set_max_concurrent(self, queue):
        queue.set_max_concurrent(5)
        assert queue._max_concurrent == 5

    def test_set_max_concurrent_clamps_low(self, queue):
        queue.set_max_concurrent(0)
        assert queue._max_concurrent == 1

    def test_set_max_concurrent_clamps_high(self, queue):
        queue.set_max_concurrent(999)
        assert queue._max_concurrent == 20


class TestPauseResume:
    def test_pause_sets_flag(self, queue):
        queue.pause()
        assert queue._paused is True

    def test_resume_clears_flag(self, queue):
        queue.pause()
        queue.resume()
        assert queue._paused is False


class TestCallbacks:
    def test_on_status_change_called_on_submit(self, queue):
        calls = []
        queue.on_status_change(lambda info: calls.append(info))
        queue.submit(Task(name="cb"))
        assert len(calls) >= 1
        assert "queued" in calls[-1]

    def test_on_progress_registered(self, queue):
        cb = lambda d: None
        queue.on_progress(cb)
        assert cb in queue._progress_callbacks


class TestUpdateProgress:
    def test_update_progress(self, queue):
        t = Task(name="prog")
        queue.submit(t)
        queue.update_progress(t.id, 50, "halfway")
        task = queue.get_task(t.id)
        assert task.progress == 50
        assert task.progress_message == "halfway"


class TestExecution:
    def test_run_simple_task(self, queue):
        """启动工作线程执行一个真实任务，验证状态流转到 COMPLETED"""
        result_box = {}

        def work():
            result_box["done"] = True
            return 42

        queue.set_max_concurrent(1)
        tid = queue.submit_function("real_work", work)
        queue.start()
        # 等待任务完成（最多 5 秒）
        deadline = time.time() + 5
        while time.time() < deadline:
            task = queue.get_task(tid)
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break
            time.sleep(0.05)
        queue.stop(wait=False)
        task = queue.get_task(tid)
        assert task.status == TaskStatus.COMPLETED
        assert result_box.get("done") is True

    def test_failing_task_marked_failed(self, queue):
        def boom():
            raise ValueError("intentional")

        queue.set_max_concurrent(1)
        tid = queue.submit_function("bad", boom, max_retries=0)
        queue.start()
        deadline = time.time() + 5
        while time.time() < deadline:
            task = queue.get_task(tid)
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                break
            time.sleep(0.05)
        queue.stop(wait=False)
        assert queue.get_task(tid).status == TaskStatus.FAILED


class TestParseStages:
    """pipeline._parse_stages 纯函数（不依赖 LLM）"""

    def test_empty_logs(self):
        from src.pipeline.pipeline import _parse_stages
        assert _parse_stages([]) == []

    def test_extracts_tool_calls(self):
        from src.pipeline.pipeline import _parse_stages
        logs = [
            {"tool_calls": [
                {"function": {"name": "browse_page", "arguments": '{"url":"x"}'}}
            ]}
        ]
        stages = _parse_stages(logs)
        assert len(stages) == 1
        assert stages[0]["tool"] == "browse_page"

    def test_multiple_calls(self):
        from src.pipeline.pipeline import _parse_stages
        logs = [
            {"tool_calls": [
                {"function": {"name": "a", "arguments": "{}"}},
                {"function": {"name": "b", "arguments": "{}"}},
            ]},
            {"tool_calls": [
                {"function": {"name": "c", "arguments": "{}"}},
            ]},
        ]
        stages = _parse_stages(logs)
        assert [s["tool"] for s in stages] == ["a", "b", "c"]

    def test_missing_tool_calls_key(self):
        from src.pipeline.pipeline import _parse_stages
        assert _parse_stages([{"other": 1}]) == []
