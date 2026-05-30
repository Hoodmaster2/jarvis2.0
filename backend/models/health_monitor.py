"""
Health monitor - tracks model performance, failures, and availability.
"""
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ModelHealthMonitor:
    def __init__(self, storage_path: str = "./data/model_health.json"):
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._metrics: dict[str, list[dict]] = defaultdict(list)
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._metrics = defaultdict(list, data.get("metrics", {}))
            except Exception:
                pass

    def _save(self):
        self.path.write_text(json.dumps({"metrics": dict(self._metrics)}, indent=2))

    def record_success(self, model: str, latency_ms: float, tokens_per_sec: float):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "latency_ms": latency_ms,
            "tokens_per_sec": tokens_per_sec,
            "status": "success",
        }
        self._metrics[model].append(entry)
        self._trim(model)
        self._save()

    def record_failure(self, model: str, error: str):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "latency_ms": 0,
            "tokens_per_sec": 0,
            "status": "failure",
            "error": error,
        }
        self._metrics[model].append(entry)
        self._trim(model)
        self._save()

    def _trim(self, model: str, max_entries: int = 1000):
        if len(self._metrics[model]) > max_entries:
            self._metrics[model] = self._metrics[model][-max_entries:]

    def get_health(self, model: str) -> dict:
        entries = self._metrics.get(model, [])
        if not entries:
            return {"status": "unknown", "avg_latency": 0, "failure_rate": 0}

        recent = entries[-100:]
        failures = sum(1 for e in recent if e["status"] == "failure")
        successes = [e for e in recent if e["status"] == "success"]
        avg_latency = sum(e["latency_ms"] for e in successes) / len(successes) if successes else 0
        avg_tps = sum(e["tokens_per_sec"] for e in successes) / len(successes) if successes else 0

        status = "healthy"
        failure_rate = failures / len(recent) if recent else 0
        if failure_rate > 0.5:
            status = "unhealthy"
        elif failure_rate > 0.2:
            status = "degraded"
        elif len(recent) < 5:
            status = "insufficient_data"

        return {
            "model": model,
            "status": status,
            "total_calls": len(entries),
            "failures": failures,
            "failure_rate": round(failure_rate, 3),
            "avg_latency_ms": round(avg_latency, 1),
            "avg_tokens_per_sec": round(avg_tps, 1),
            "last_checked": datetime.utcnow().isoformat(),
        }

    def get_all_health(self) -> dict[str, dict]:
        return {m: self.get_health(m) for m in self._metrics}

    def get_best_model(self, candidates: list[str]) -> Optional[str]:
        best = None
        best_score = -1
        for model in candidates:
            health = self.get_health(model)
            if health["status"] == "unhealthy":
                continue
            score = health.get("avg_tokens_per_sec", 0) - health.get("avg_latency_ms", 0) / 100
            if health["failure_rate"] > 0.3:
                score -= 10
            if score > best_score:
                best_score = score
                best = model
        return best

    def is_available(self, model: str) -> bool:
        health = self.get_health(model)
        return health["status"] != "unhealthy"

    def get_summary(self) -> dict:
        all_health = self.get_all_health()
        total = len(all_health)
        healthy = sum(1 for h in all_health.values() if h["status"] == "healthy")
        degraded = sum(1 for h in all_health.values() if h["status"] == "degraded")
        unhealthy = sum(1 for h in all_health.values() if h["status"] == "unhealthy")
        return {
            "total_models": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "models": all_health,
        }

    def clear(self):
        self._metrics.clear()
        self._save()
