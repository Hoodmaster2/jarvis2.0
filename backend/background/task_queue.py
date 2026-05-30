import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueTask:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    handler: Callable = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0


class TaskQueue:
    def __init__(self, max_concurrent: int = 5):
        self._queue = asyncio.PriorityQueue()
        self._running: set = set()
        self._completed: list = []
        self._max_concurrent = max_concurrent
        self._max_completed = 200
        self._worker_task = None
        self._running_flag = False

    async def start(self):
        self._running_flag = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(f"Task queue started (max_concurrent={self._max_concurrent})")

    async def stop(self):
        self._running_flag = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def enqueue(self, task: QueueTask):
        await self._queue.put((task.priority, task))
        logger.debug(f"Enqueued task: {task.name} ({task.id})")

    async def _worker_loop(self):
        while self._running_flag:
            if len(self._running) >= self._max_concurrent:
                await asyncio.sleep(0.1)
                continue
            try:
                _, task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            self._running.add(task.id)
            asyncio.create_task(self._execute(task))

    async def _execute(self, task: QueueTask):
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        try:
            result = task.handler(*task.args, **task.kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            task.result = result
            task.status = TaskStatus.COMPLETED
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            logger.error(f"Task {task.name} failed: {e}")
        task.completed_at = time.time()
        self._running.discard(task.id)
        self._completed.append(task)
        if len(self._completed) > self._max_completed:
            self._completed = self._completed[-self._max_completed:]

    def get_status(self) -> dict:
        return {
            "pending": self._queue.qsize(),
            "running": len(self._running),
            "completed": len(self._completed),
        }

    def get_completed(self, limit: int = 50) -> list:
        return [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status.value,
                "error": t.error,
                "created_at": t.created_at,
                "completed_at": t.completed_at,
                "duration": t.completed_at - t.started_at if t.completed_at and t.started_at else 0,
            }
            for t in self._completed[-limit:]
        ]

    def cancel(self, task_id: str) -> bool:
        for t in self._completed:
            if t.id == task_id and t.status == TaskStatus.PENDING:
                t.status = TaskStatus.CANCELLED
                return True
        return False
