"""
Advanced model router with task-based routing, health checks, load balancing, and fallbacks.
"""
import logging
import time
from typing import Optional

from .model_registry import ModelRegistry
from .model_profiles import MODEL_PROFILES, TASK_TO_CAPABILITY
from .health_monitor import ModelHealthMonitor
from .load_balancer import LoadBalancer
from .fallback_manager import FallbackManager

logger = logging.getLogger(__name__)


class ModelRouter:
    DEFAULT_MODEL = "qwen3"
    EMBEDDING_MODEL = "nomic-embed-text"

    def __init__(self, ollama_client, default_model: str = None):
        self.ollama = ollama_client
        self._default = default_model or self.DEFAULT_MODEL
        self._agent_models: dict[str, str] = {}
        self._force_model: Optional[str] = None
        self._disabled_models: list[str] = []

        self.registry = ModelRegistry(ollama_client)
        self.health = ModelHealthMonitor()
        self.balancer = LoadBalancer(self.health)
        self.fallback = FallbackManager(self.health, self.registry)
        self._model_capabilities: dict[str, list[str]] = {}
        self._loaded_context: dict[str, list[dict]] = {}
        self._warmed_up: set[str] = set()

    async def refresh(self):
        await self.registry.refresh()

    def assign_model(self, agent_name: str, model: str):
        self._agent_models[agent_name] = model
        logger.info(f"Agent '{agent_name}' assigned to model '{model}'")

    def get_model_for(self, agent_name: str, task_type: str = None) -> str:
        if self._force_model:
            return self._force_model
        if agent_name in self._agent_models:
            return self._agent_models[agent_name]
        if task_type:
            cap = TASK_TO_CAPABILITY.get(task_type, "chat")
            candidates = self.registry.get_by_capability(cap)
            available = [m["name"] for m in candidates
                         if m["name"] not in self._disabled_models]
            if available:
                selected = self.balancer.select(available, task_type)
                if selected:
                    return selected
            fallback = self.fallback.find_available(task_type)
            if fallback:
                return fallback

        return self._default

    def get_embedding_model(self) -> str:
        models = self.registry.get_by_capability("embeddings")
        if models:
            return models[0]["name"]
        return self.EMBEDDING_MODEL

    def force_model(self, model: str):
        self._force_model = model
        logger.info(f"Model forced to '{model}'")

    def release_force(self):
        self._force_model = None
        logger.info("Model force released")

    def disable_model(self, model: str):
        if model not in self._disabled_models:
            self._disabled_models.append(model)

    def enable_model(self, model: str):
        if model in self._disabled_models:
            self._disabled_models.remove(model)

    def record_success(self, model: str, latency_ms: float, tokens_per_sec: float):
        self.health.record_success(model, latency_ms, tokens_per_sec)

    def record_failure(self, model: str, error: str):
        self.health.record_failure(model, error)

    def set_balancer_strategy(self, strategy: str):
        self.balancer.set_strategy(strategy)

    def analyze_task(self, task: str) -> dict:
        task_lower = task.lower()
        task_type = "chat"
        complexity = 1
        vision = any(k in task_lower for k in ["see", "look", "image", "picture", "photo", "screenshot"])
        coding = any(k in task_lower for k in ["code", "write", "function", "class", "debug", "fix", "implement"])
        planning = any(k in task_lower for k in ["plan", "strategy", "step", "workflow", "multi-step"])

        if vision:
            task_type = "vision"
            complexity = 3
        elif coding:
            task_type = "coding"
            complexity = 3 if planning else 2
        elif planning:
            task_type = "planning"
            complexity = 3

        if len(task) > 500:
            complexity += 1

        return {"task_type": task_type, "complexity": complexity, "needs_vision": vision}

    def get_routing_decision(self, task: str, agent_name: str = "") -> dict:
        analysis = self.analyze_task(task)
        chosen = self.get_model_for(agent_name, analysis["task_type"])
        return {
            "chosen_model": chosen,
            "task_type": analysis["task_type"],
            "complexity": analysis["complexity"],
            "needs_vision": analysis["needs_vision"],
            "agent": agent_name or "default",
            "available_models": [m["name"] for m in self.registry.get_installed_list()
                                 if m["name"] not in self._disabled_models],
        }

    def get_status(self) -> dict:
        return {
            "default_model": self._default,
            "forced_model": self._force_model,
            "disabled_models": self._disabled_models,
            "agent_assignments": self._agent_models,
            "health_summary": self.health.get_summary(),
            "installed": len(self.registry.get_installed_list()),
            "balancer_strategy": self.balancer._current_strategy,
            "warmed_up": list(self._warmed_up),
        }

    async def warm_up(self, model: str):
        if model in self._warmed_up:
            return
        try:
            await self.ollama.generate(model, "Warm up", max_tokens=1)
            self._warmed_up.add(model)
            logger.info(f"Warmed up model '{model}'")
        except Exception as e:
            logger.warning(f"Failed to warm up model '{model}': {e}")
