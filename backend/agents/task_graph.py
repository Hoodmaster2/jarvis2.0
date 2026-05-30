"""
Task Graph - DAG-based task execution with dependencies, retries, and parallel branches.
"""
import asyncio
import json
import logging
import time
import uuid
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class Task:
    """A single task node in the DAG."""

    def __init__(
        self,
        task_id: str,
        agent: str,
        action: str,
        params: dict = None,
        depends_on: list = None,
        priority: int = 0,
        max_retries: int = 2,
        timeout: float = 120.0,
        metadata: dict = None,
    ):
        self.id = task_id or str(uuid.uuid4())
        self.agent = agent
        self.action = action
        self.params = params or {}
        self.depends_on = depends_on or []
        self.priority = priority
        self.max_retries = max_retries
        self.timeout = timeout
        self.metadata = metadata or {}
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.retry_count = 0
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.assigned_to = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent": self.agent,
            "action": self.action,
            "params": self.params,
            "depends_on": self.depends_on,
            "priority": self.priority,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "metadata": self.metadata,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class TaskGraph:
    """DAG-based task execution graph."""

    def __init__(self, graph_id: str = None):
        self.id = graph_id or str(uuid.uuid4())
        self.tasks: dict[str, Task] = {}
        self._adjacency: dict[str, list[str]] = {}  # task_id -> list of dependents
        self._reverse_adj: dict[str, list[str]] = {}  # task_id -> list of dependencies
        self.created_at = time.time()
        self.completed_at = None
        self.status = TaskStatus.PENDING
        self.metadata = {}

    def add_task(self, task: Task):
        """Add a task to the graph."""
        self.tasks[task.id] = task
        self._adjacency[task.id] = []
        self._reverse_adj[task.id] = task.depends_on[:]
        for dep_id in task.depends_on:
            if dep_id not in self._adjacency:
                self._adjacency[dep_id] = []
            self._adjacency[dep_id].append(task.id)

    def get_ready_tasks(self) -> list[Task]:
        """Get tasks whose dependencies are all completed."""
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            deps = self._reverse_adj.get(task.id, [])
            if all(self.tasks[d].status == TaskStatus.COMPLETED for d in deps if d in self.tasks):
                ready.append(task)
        # Sort by priority (higher first)
        ready.sort(key=lambda t: t.priority, reverse=True)
        return ready

    def has_unfinished_tasks(self) -> bool:
        """Check if there are any unfinished tasks."""
        return any(
            t.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.BLOCKED)
            for t in self.tasks.values()
        )

    def get_task_count(self, status: TaskStatus = None) -> int:
        if status:
            return sum(1 for t in self.tasks.values() if t.status == status)
        return len(self.tasks)

    def mark_completed(self, task_id: str, result: Any = None):
        task = self.tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()
            self._check_graph_completion()

    def mark_failed(self, task_id: str, error: str = None):
        task = self.tasks.get(task_id)
        if task:
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                logger.info(f"Task {task_id} will retry ({task.retry_count}/{task.max_retries})")
            else:
                task.status = TaskStatus.FAILED
                task.error = error
                task.completed_at = time.time()
                self._fail_dependents(task_id)
                self._check_graph_completion()

    def _fail_dependents(self, task_id: str):
        for dep_id in self._adjacency.get(task_id, []):
            dep = self.tasks.get(dep_id)
            if dep and dep.status == TaskStatus.PENDING:
                dep.status = TaskStatus.BLOCKED
                dep.error = f"Dependency {task_id} failed"
                self._fail_dependents(dep_id)

    def _check_graph_completion(self):
        if not self.has_unfinished_tasks():
            self.completed_at = time.time()
            all_ok = all(
                t.status == TaskStatus.COMPLETED
                for t in self.tasks.values()
            )
            self.status = TaskStatus.COMPLETED if all_ok else TaskStatus.FAILED
            logger.info(f"TaskGraph {self.id} completed with status {self.status.value}")

    def cancel(self, task_id: str = None):
        """Cancel a task or the entire graph."""
        if task_id:
            task = self.tasks.get(task_id)
            if task and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.CANCELLED
                self._fail_dependents(task_id)
        else:
            for task in self.tasks.values():
                if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.BLOCKED):
                    task.status = TaskStatus.CANCELLED
            self.status = TaskStatus.CANCELLED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tasks": [t.to_dict() for t in self.tasks.values()],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "status": self.status.value,
            "metadata": self.metadata,
            "task_count": len(self.tasks),
            "completed_count": self.get_task_count(TaskStatus.COMPLETED),
            "failed_count": self.get_task_count(TaskStatus.FAILED),
        }

    def to_dag_json(self) -> dict:
        """Return a DAG visualization-friendly structure."""
        return {
            "nodes": [
                {
                    "id": t.id,
                    "label": t.action,
                    "agent": t.agent,
                    "status": t.status.value,
                    "priority": t.priority,
                }
                for t in self.tasks.values()
            ],
            "edges": [
                {"from": dep_id, "to": t.id}
                for t in self.tasks.values()
                for dep_id in t.depends_on
                if dep_id in self.tasks
            ],
        }
