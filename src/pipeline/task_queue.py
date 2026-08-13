"""
任务队列 — 并发控制 + 任务隔离
每个资源使用独立的 Agent 实例，通过全局锁控制并发数量
详见架构文档 §10
"""
import time
import threading
import queue
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

from loguru import logger


class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


@dataclass
class Task:
    """单个任务"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    func: Optional[Callable] = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    resource_id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    progress: int = 0          # 0-100
    progress_message: str = ""
    max_retries: int = 3
    retry_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.name,
            "status": self.status.value,
            "resource_id": self.resource_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": str(self.result)[:200] if self.result else None,
            "error": self.error,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "retry_count": self.retry_count,
        }


class TaskQueue:
    """
    任务队列管理器 — 全局单例

    特性:
    - 优先级队列（CRITICAL > HIGH > NORMAL > LOW）
    - 最大并发控制（默认 3 个并行任务）
    - 任务隔离（每个任务独立异常处理）
    - 进度回调（支持 WebSocket 实时推送）
    - 暂停/恢复/取消
    """

    _instance: Optional["TaskQueue"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._queue: queue.PriorityQueue = queue.PriorityQueue()
            self._active: dict[str, Task] = {}
            self._history: dict[str, Task] = {}
            self._max_concurrent: int = 3
            self._semaphore = threading.BoundedSemaphore(3)
            self._paused: bool = False
            self._running: bool = False
            self._worker_thread: Optional[threading.Thread] = None
            self._progress_callbacks: list[Callable] = []
            self._status_callback: Optional[Callable] = None
            self._task_lock = threading.Lock()
            self._submit_counter = 0  # 单调递增计数，保证堆元组前两项唯一

    # ===== 任务管理 =====

    def submit(self, task: Task) -> str:
        """提交任务到队列，返回任务 ID"""
        with self._task_lock:
            self._history[task.id] = task
            # PriorityQueue 使用 (priority, counter, task) 避免比较 task；
            # counter 必须唯一且递增（time.time() 可能相同导致 heappush 比较 Task）
            self._submit_counter += 1
            self._queue.put((-task.priority.value, self._submit_counter, task))
        logger.info(f"📋 任务入队: {task.name} ({task.id})")
        self._notify_status()
        return task.id

    def submit_function(
        self,
        name: str,
        func: Callable,
        *args,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        resource_id: int = None,
        max_retries: int = 3,
        **kwargs,
    ) -> str:
        """便捷方法：提交一个函数作为任务"""
        task = Task(
            name=name,
            description=description or name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            resource_id=resource_id,
            max_retries=max_retries,
        )
        return self.submit(task)

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        with self._task_lock:
            task = self._history.get(task_id)
            if not task:
                return False
            if task.status == TaskStatus.QUEUED:
                task.status = TaskStatus.CANCELLED
                logger.info(f"🚫 任务取消: {task.name} ({task_id})")
            elif task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.CANCELLED
                logger.info(f"🚫 正在取消运行中的任务: {task.name} ({task_id})")
            self._notify_status()
            return True

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务详情"""
        return self._history.get(task_id)

    def get_active_tasks(self) -> list[dict]:
        """获取当前活跃任务列表"""
        with self._task_lock:
            return [t.to_dict() for t in self._active.values()]

    def get_queued_tasks(self) -> list[dict]:
        """获取等待队列"""
        with self._task_lock:
            all_items = list(self._queue.queue)
            return [
                self._history[item[2].id].to_dict()
                for item in all_items
                if item[2].id in self._history
            ]

    def get_all_tasks(self) -> list[dict]:
        """获取所有任务（含历史）"""
        with self._task_lock:
            return [t.to_dict() for t in self._history.values()]

    def get_queue_size(self) -> int:
        """获取队列长度"""
        return self._queue.qsize()

    def get_active_count(self) -> int:
        """获取活跃任务数"""
        with self._task_lock:
            return len(self._active)

    # ===== 并发控制 =====

    def set_max_concurrent(self, n: int):
        """设置最大并发数"""
        if n < 1:
            n = 1
        if n > 20:
            n = 20
        old = self._max_concurrent
        self._max_concurrent = n
        # 重建信号量
        self._semaphore = threading.BoundedSemaphore(n)
        logger.info(f"🔧 最大并发数: {old} → {n}")

    def pause(self):
        """暂停处理新任务（不影响正在运行的）"""
        self._paused = True
        logger.info("⏸️ 任务队列已暂停")

    def resume(self):
        """恢复处理"""
        self._paused = False
        logger.info("▶️ 任务队列已恢复")

    # ===== 回调机制 =====

    def on_progress(self, callback: Callable):
        """注册进度回调（用于 WebSocket 推送）"""
        self._progress_callbacks.append(callback)

    def on_status_change(self, callback: Callable):
        """注册状态回调"""
        self._status_callback = callback

    def _notify_progress(self, task: Task):
        """通知进度更新"""
        for cb in self._progress_callbacks:
            try:
                cb(task.to_dict())
            except Exception as e:
                logger.error(f"进度回调异常: {e}")

    def _notify_status(self):
        """通知状态变更"""
        if self._status_callback:
            try:
                self._status_callback({
                    "active": self.get_active_count(),
                    "queued": self.get_queue_size(),
                    "total": len(self._history),
                    "paused": self._paused,
                })
            except Exception as e:
                logger.error(f"状态回调异常: {e}")

    # ===== 工作循环 =====

    def start(self):
        """启动任务队列工作线程"""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info(f"⚙️ 任务队列已启动 (最大并发: {self._max_concurrent})")

    def stop(self, wait: bool = True):
        """停止任务队列"""
        self._running = False
        if wait and self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=30)
        logger.info("🛑 任务队列已停止")

    def _worker_loop(self):
        """工作线程主循环"""
        while self._running:
            if self._paused:
                time.sleep(1)
                continue

            try:
                # 非阻塞获取任务，超时 1 秒后重新检查 _running
                priority_neg, ts, task = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            # 检查任务是否已被取消
            if task.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue

            # 获取信号量（限并发）
            self._semaphore.acquire()

            # 在新线程中执行任务
            t = threading.Thread(target=self._execute_task, args=(task,), daemon=True)
            t.start()

    def _execute_task(self, task: Task):
        """执行单个任务"""
        with self._task_lock:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            self._active[task.id] = task

        self._notify_status()
        logger.info(f"▶️ 任务开始: {task.name} ({task.id})")

        try:
            while task.retry_count <= task.max_retries:
                if task.status == TaskStatus.CANCELLED:
                    break

                try:
                    if task.func:
                        task.result = task.func(*task.args, **task.kwargs)
                    task.status = TaskStatus.COMPLETED
                    task.progress = 100
                    task.progress_message = "完成"
                    logger.info(f"✅ 任务完成: {task.name} ({task.id})")
                    break

                except Exception as e:
                    task.retry_count += 1
                    task.error = str(e)
                    logger.warning(
                        f"⚠️ 任务失败 (重试 {task.retry_count}/{task.max_retries}): "
                        f"{task.name} ({task.id}): {e}"
                    )

                    if task.retry_count > task.max_retries:
                        task.status = TaskStatus.FAILED
                    else:
                        time.sleep(min(2 ** task.retry_count, 60))  # 指数退避

        finally:
            task.finished_at = datetime.now().isoformat()
            with self._task_lock:
                self._active.pop(task.id, None)
            self._semaphore.release()
            self._queue.task_done()
            self._notify_progress(task)
            self._notify_status()

    def update_progress(self, task_id: str, progress: int, message: str = ""):
        """更新任务进度（由执行函数调用）"""
        with self._task_lock:
            task = self._history.get(task_id)
            if task:
                task.progress = progress
                task.progress_message = message
                self._notify_progress(task)


# 全局任务队列实例
_task_queue_instance: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """获取全局任务队列单例"""
    global _task_queue_instance
    if _task_queue_instance is None:
        _task_queue_instance = TaskQueue()
    return _task_queue_instance


def submit_task(
    name: str,
    func: Callable,
    *args,
    description: str = "",
    priority: TaskPriority = TaskPriority.NORMAL,
    resource_id: int = None,
    **kwargs,
) -> str:
    """便捷提交任务"""
    return get_task_queue().submit_function(
        name=name,
        func=func,
        *args,
        description=description,
        priority=priority,
        resource_id=resource_id,
        **kwargs,
    )
