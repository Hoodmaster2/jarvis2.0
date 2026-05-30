"""
Fallback manager - handles model failures by routing to fallback models.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

FALLBACK_CHAINS = {
    "code": ["deepseek-coder", "qwen3", "qwen2.5", "llama3.1"],
    "chat": ["qwen3", "qwen2.5", "llama3.2", "phi4"],
    "vision": ["llava", "qwen-vl", "qwen3"],
    "reasoning": ["deepseek-r1", "qwen3", "qwen2.5"],
    "embedding": ["nomic-embed-text", "mxbai-embed-large"],
    "planning": ["qwen3", "deepseek-r1", "qwen2.5"],
    "lightweight": ["phi4", "phi3", "llama3.2"],
    "default": ["qwen3", "qwen2.5", "llama3.2", "mistral"],
}


class FallbackManager:
    def __init__(self, health_monitor, registry):
        self._health = health_monitor
        self._registry = registry
        self._chains = FALLBACK_CHAINS

    def get_fallback_chain(self, task_type: str) -> list[str]:
        return self._chains.get(task_type, self._chains["default"])

    def find_available(self, task_type: str, prefer_installed: bool = True) -> Optional[str]:
        chain = self.get_fallback_chain(task_type)
        installed = {m["name"] for m in self._registry.get_installed_list()}

        for model in chain:
            if prefer_installed and model not in installed:
                continue
            if self._health.is_available(model):
                return model

        for model in chain:
            if prefer_installed and model not in installed:
                continue
            if self._health.get_health(model)["status"] != "unhealthy":
                return model

        return chain[0] if chain else None

    def get_all_chains(self) -> dict[str, list[str]]:
        return dict(self._chains)

    def set_chain(self, task_type: str, models: list[str]):
        self._chains[task_type] = models
