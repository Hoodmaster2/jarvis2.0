"""
Load balancer - distributes requests across healthy models to optimize performance.
"""
import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)


class LoadBalancer:
    def __init__(self, health_monitor):
        self._health = health_monitor
        self._strategies = {
            "round_robin": self._round_robin,
            "least_load": self._least_load,
            "random": self._random,
            "fastest": self._fastest,
        }
        self._current_strategy = "least_load"
        self._rr_index: dict[str, int] = {}

    def set_strategy(self, strategy: str):
        if strategy in self._strategies:
            self._current_strategy = strategy
            logger.info(f"Load balancer strategy set to '{strategy}'")

    def select(self, candidates: list[str], task_type: str = "") -> Optional[str]:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        return self._strategies[self._current_strategy](candidates)

    def _round_robin(self, candidates: list[str]) -> str:
        key = "_global"
        self._rr_index.setdefault(key, -1)
        self._rr_index[key] = (self._rr_index[key] + 1) % len(candidates)
        return candidates[self._rr_index[key]]

    def _least_load(self, candidates: list[str]) -> str:
        healths = [(m, self._health.get_health(m)) for m in candidates]
        healths.sort(key=lambda x: (
            x[1].get("failure_rate", 1),
            x[1].get("avg_latency_ms", 9999),
        ))
        for model, health in healths:
            if health["status"] != "unhealthy":
                return model
        return candidates[0]

    def _random(self, candidates: list[str]) -> str:
        return random.choice(candidates)

    def _fastest(self, candidates: list[str]) -> str:
        healths = [(m, self._health.get_health(m)) for m in candidates]
        healths.sort(key=lambda x: x[1].get("avg_latency_ms", 9999))
        for model, health in healths:
            if health["status"] != "unhealthy":
                return model
        return candidates[0]
