import asyncio
import logging
import time
from typing import Optional

from .event_bus import BackgroundEventBus, Event, EventPriority
from .task_queue import TaskQueue
from .scheduler import Scheduler, ScheduledTask
from .observers import ObserverRegistry, create_system_observer
from .notifications import NotificationManager

logger = logging.getLogger(__name__)


class BackgroundDaemon:
    def __init__(self):
        self.event_bus = BackgroundEventBus()
        self.task_queue = TaskQueue(max_concurrent=5)
        self.scheduler = Scheduler()
        self.observers = ObserverRegistry()
        self.notifications = NotificationManager()
        self._running = False
        self._health_task = None
        self._start_time = 0.0

    async def start(self):
        self._running = True
        self._start_time = time.time()
        await self.event_bus.start()
        await self.task_queue.start()
        await self.scheduler.start()

        self.observers.set_event_callback(self._on_observer_event)
        self.observers.register(create_system_observer("system", 60.0))
        await self.observers.start()

        self.event_bus.subscribe("notification", self._handle_notification_event)

        self._health_task = asyncio.create_task(self._health_loop())
        logger.info("Background daemon started")

    async def stop(self):
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        await self.observers.stop()
        await self.scheduler.stop()
        await self.task_queue.stop()
        await self.event_bus.stop()
        logger.info("Background daemon stopped")

    async def _on_observer_event(self, data: dict):
        await self.event_bus.publish(Event(
            type=f"observer.{data['observer']}",
            payload=data,
            sender="observers",
            priority=EventPriority.LOW,
        ))

    async def _handle_notification_event(self, event: Event):
        if isinstance(event.payload, dict):
            self.notifications.info(
                title=event.payload.get("title", "Event"),
                message=event.payload.get("message", ""),
                source=event.sender,
            )

    async def _health_loop(self):
        while self._running:
            uptime = time.time() - self._start_time
            queue_status = self.task_queue.get_status()
            await self.event_bus.publish(Event(
                type="daemon.health",
                payload={
                    "uptime": uptime,
                    "queue": queue_status,
                    "scheduled_tasks": len(self.scheduler.get_tasks()),
                    "notifications": self.notifications.get_unread_count(),
                },
                sender="daemon",
                priority=EventPriority.LOW,
            ))
            await asyncio.sleep(60)

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "uptime": time.time() - self._start_time if self._start_time else 0,
            "queue": self.task_queue.get_status(),
            "scheduled_tasks": len(self.scheduler.get_tasks()),
            "notifications": {
                "total": len(self.notifications.get_notifications(limit=1000)),
                "unread": self.notifications.get_unread_count(),
            },
            "observers": self.observers.get_observers(),
        }
