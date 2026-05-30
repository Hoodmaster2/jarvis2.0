import asyncio
import logging
import time
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    type: str
    payload: Any = None
    sender: str = ""
    priority: EventPriority = EventPriority.NORMAL
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: float = field(default_factory=time.time)


EventHandler = Callable[[Event], Any]


class BackgroundEventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._history: List[Event] = []
        self._max_history = 500
        self._running = False
        self._queue: asyncio.Queue = None
        self._worker_task = None

    async def start(self):
        self._running = True
        self._queue = asyncio.Queue()
        self._worker_task = asyncio.create_task(self._process_loop())
        logger.info("Background event bus started")

    async def stop(self):
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Background event bus stopped")

    def subscribe(self, event_type: str, handler: EventHandler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to '{event_type}': {handler.__name__}")

    def unsubscribe(self, event_type: str, handler: EventHandler):
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: Event):
        if self._queue:
            await self._queue.put(event)
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    async def _process_loop(self):
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._dispatch(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event bus error: {e}")

    async def _dispatch(self, event: Event):
        handlers = self._subscribers.get(event.type, []) + self._subscribers.get("*", [])
        if not handlers:
            return
        results = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event)
                else:
                    result = handler(event)
                results.append(result)
            except Exception as e:
                logger.error(f"Handler {handler.__name__} failed for {event.type}: {e}")
        return results

    def get_history(self, limit: int = 100, event_type: str = None) -> list:
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return [
            {
                "id": e.id,
                "type": e.type,
                "sender": e.sender,
                "priority": e.priority.name,
                "timestamp": e.timestamp,
                "payload": str(e.payload)[:200],
            }
            for e in events[-limit:]
        ]

    def clear_history(self):
        self._history = []
