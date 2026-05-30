import asyncio
import logging
import time
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Observer:
    name: str
    check_fn: Callable
    interval: float = 30.0
    enabled: bool = True
    last_check: float = 0.0
    on_event: Optional[Callable] = None

    async def check(self) -> Optional[dict]:
        if not self.enabled:
            return None
        try:
            result = self.check_fn()
            if asyncio.iscoroutine(result):
                result = await result
            self.last_check = time.time()
            return result
        except Exception as e:
            logger.warning(f"Observer '{self.name}' check failed: {e}")
            return None


class ObserverRegistry:
    def __init__(self):
        self._observers: list = []
        self._running = False
        self._loop_task = None
        self._event_callback: Optional[Callable] = None

    def set_event_callback(self, callback: Callable):
        self._event_callback = callback

    def register(self, observer: Observer):
        self._observers.append(observer)
        logger.info(f"Registered observer: {observer.name} (interval={observer.interval}s)")

    def unregister(self, name: str) -> bool:
        for i, obs in enumerate(self._observers):
            if obs.name == name:
                self._observers.pop(i)
                return True
        return False

    async def start(self):
        self._running = True
        self._loop_task = asyncio.create_task(self._observer_loop())
        logger.info(f"Observer registry started with {len(self._observers)} observers")

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _observer_loop(self):
        while self._running:
            now = time.time()
            for obs in self._observers:
                if obs.enabled and (now - obs.last_check) >= obs.interval:
                    result = await obs.check()
                    if result and self._event_callback:
                        await self._event_callback({
                            "observer": obs.name,
                            "data": result,
                            "timestamp": now,
                        })
            await asyncio.sleep(5)

    def get_observers(self) -> list:
        return [
            {
                "name": o.name,
                "interval": o.interval,
                "enabled": o.enabled,
                "last_check": o.last_check,
            }
            for o in self._observers
        ]

    def set_enabled(self, name: str, enabled: bool) -> bool:
        for obs in self._observers:
            if obs.name == name:
                obs.enabled = enabled
                return True
        return False


def create_system_observer(name: str = "system", interval: float = 60.0) -> Observer:
    def check_system():
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            }
        except ImportError:
            return {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0}
    return Observer(name=name, check_fn=check_system, interval=interval)


def create_powershell_observer(name: str = "powershell", interval: float = 120.0) -> Observer:
    def check_processes():
        import psutil
        ps_count = 0
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and "powershell" in proc.info["name"].lower():
                    ps_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return {"powershell_process_count": ps_count}
    return Observer(name=name, check_fn=check_processes, interval=interval)
