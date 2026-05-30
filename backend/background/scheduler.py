import asyncio
import logging
import time
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4
import re

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    cron_expr: str = ""
    interval_seconds: int = 0
    handler: Callable = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    enabled: bool = True
    last_run: float = 0.0
    next_run: float = 0.0
    run_count: int = 0
    created_at: float = field(default_factory=time.time)

    def is_due(self, now: float = None) -> bool:
        if not self.enabled:
            return False
        now = now or time.time()
        return now >= self.next_run

    def compute_next_run(self):
        now = time.time()
        if self.cron_expr:
            try:
                minute, hour, dom, month, dow = self.cron_expr.strip().split()
                parts = [self._parse_cron_field(minute, 0, 59),
                         self._parse_cron_field(hour, 0, 23),
                         self._parse_cron_field(dom, 1, 31),
                         self._parse_cron_field(month, 1, 12),
                         self._parse_cron_field(dow, 0, 6)]
                dt = datetime.fromtimestamp(now) + timedelta(minutes=1)
                dt = dt.replace(second=0, microsecond=0)
                for _ in range(525600):
                    if self._match_cron(dt, parts):
                        self.next_run = dt.timestamp()
                        return
                    dt += timedelta(minutes=1)
                self.next_run = now + 3600
            except Exception as e:
                logger.warning(f"Failed to parse cron '{self.cron_expr}': {e}")
                self.next_run = now + self.interval_seconds if self.interval_seconds else now + 3600
        elif self.interval_seconds > 0:
            self.next_run = now + self.interval_seconds
        else:
            self.next_run = now + 3600

    def _parse_cron_field(self, field: str, min_val: int, max_val: int):
        if field == "*":
            return list(range(min_val, max_val + 1))
        values = []
        for part in field.split(","):
            if "/" in part:
                base, step = part.split("/")
                start = min_val if base == "*" else int(base)
                values.extend(range(start, max_val + 1, int(step)))
            elif "-" in part:
                a, b = part.split("-")
                values.extend(range(int(a), int(b) + 1))
            else:
                values.append(int(part))
        return sorted(set(v for v in values if min_val <= v <= max_val))

    def _match_cron(self, dt: datetime, parts: list) -> bool:
        minute, hour, dom, month, dow = parts
        return (dt.minute in minute and dt.hour in hour and
                dt.day in dom and dt.month in month and
                dt.weekday() in dow)


class Scheduler:
    def __init__(self):
        self._tasks: dict = {}
        self._running = False
        self._tick_task = None

    async def start(self):
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop())
        logger.info("Scheduler started")

    async def stop(self):
        self._running = False
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass

    def add_task(self, task: ScheduledTask):
        task.compute_next_run()
        self._tasks[task.id] = task
        logger.info(f"Scheduled task '{task.name}' (id={task.id[:8]}...) next_run={datetime.fromtimestamp(task.next_run)}")
        return task.id

    def remove_task(self, task_id: str) -> bool:
        return self._tasks.pop(task_id, None) is not None

    def get_task(self, task_id: str) -> Optional[dict]:
        task = self._tasks.get(task_id)
        if task:
            return self._task_to_dict(task)
        return None

    def get_tasks(self) -> list:
        return [self._task_to_dict(t) for t in self._tasks.values()]

    def _task_to_dict(self, task: ScheduledTask) -> dict:
        return {
            "id": task.id,
            "name": task.name,
            "cron_expr": task.cron_expr,
            "interval_seconds": task.interval_seconds,
            "enabled": task.enabled,
            "last_run": task.last_run,
            "next_run": task.next_run,
            "run_count": task.run_count,
            "created_at": task.created_at,
        }

    async def _tick_loop(self):
        while self._running:
            now = time.time()
            for task in self._tasks.values():
                if task.is_due(now):
                    asyncio.create_task(self._run_task(task))
                    task.compute_next_run()
            await asyncio.sleep(10)

    async def _run_task(self, task: ScheduledTask):
        task.last_run = time.time()
        task.run_count += 1
        logger.info(f"Running scheduled task: {task.name}")
        try:
            result = task.handler(*task.args, **task.kwargs)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"Scheduled task '{task.name}' failed: {e}")
