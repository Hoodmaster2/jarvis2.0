"""
Model registry - detects installed models, their capabilities, and performance profiles.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_PROFILES = {
    "qwen3": {"capabilities": ["planning", "chat", "reasoning", "coding"], "context": 32768, "type": "general"},
    "qwen2.5": {"capabilities": ["chat", "reasoning", "coding"], "context": 32768, "type": "general"},
    "deepseek-coder": {"capabilities": ["coding", "reasoning"], "context": 16384, "type": "coding"},
    "deepseek-r1": {"capabilities": ["reasoning", "planning", "coding"], "context": 32768, "type": "reasoning"},
    "llama3.2": {"capabilities": ["chat", "reasoning"], "context": 8192, "type": "general"},
    "llama3.1": {"capabilities": ["chat", "reasoning", "coding"], "context": 8192, "type": "general"},
    "mistral": {"capabilities": ["chat", "reasoning", "coding"], "context": 8192, "type": "general"},
    "phi3": {"capabilities": ["chat", "reasoning"], "context": 4096, "type": "lightweight"},
    "phi4": {"capabilities": ["chat", "reasoning", "coding"], "context": 16384, "type": "lightweight"},
    "llava": {"capabilities": ["vision", "chat"], "context": 4096, "type": "vision"},
    "llava-llama3": {"capabilities": ["vision", "chat", "reasoning"], "context": 8192, "type": "vision"},
    "qwen-vl": {"capabilities": ["vision", "chat", "reasoning"], "context": 8192, "type": "vision"},
    "nomic-embed-text": {"capabilities": ["embeddings"], "context": 8192, "type": "embedding"},
    "mxbai-embed-large": {"capabilities": ["embeddings"], "context": 512, "type": "embedding"},
}


class ModelRegistry:
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self._installed: dict[str, dict] = {}
        self._custom_profiles: dict[str, dict] = {}
        self._profile_path = Path("./data/model_profiles.json")
        self._profile_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_custom()

    async def refresh(self):
        try:
            models = await self.ollama.list_models()
            self._installed = {}
            for m in models:
                name = m.get("name", "")
                base = name.split(":")[0]
                profile = MODEL_PROFILES.get(base, {})
                self._installed[name] = {
                    "name": name,
                    "base": base,
                    "capabilities": profile.get("capabilities", ["chat"]),
                    "context": profile.get("context", 4096),
                    "type": profile.get("type", "general"),
                    "digest": m.get("digest", "")[:12],
                    "size": m.get("size", 0),
                    "modified_at": m.get("modified_at", ""),
                }
            logger.info(f"Refreshed model registry: {len(self._installed)} models")
        except Exception as e:
            logger.warning(f"Failed to refresh model registry: {e}")

    def get_installed(self) -> dict[str, dict]:
        return dict(self._installed)

    def get_installed_list(self) -> list[dict]:
        return list(self._installed.values())

    def get_by_capability(self, capability: str) -> list[dict]:
        return [
            m for m in self._installed.values()
            if capability in m.get("capabilities", [])
        ]

    def get_best_for_task(self, task_type: str) -> Optional[str]:
        capability_map = {
            "coding": "coding",
            "planning": "planning",
            "vision": "vision",
            "chat": "chat",
            "reasoning": "reasoning",
            "embedding": "embeddings",
            "lightweight": "chat",
        }
        cap = capability_map.get(task_type, "chat")
        candidates = self.get_by_capability(cap)
        if not candidates:
            return None
        candidates.sort(key=lambda m: -m.get("context", 4096))
        return candidates[0]["name"]

    def get_profile(self, model_name: str) -> dict:
        base = model_name.split(":")[0]
        return self._custom_profiles.get(model_name, MODEL_PROFILES.get(base, {}))

    def set_profile(self, model_name: str, profile: dict):
        self._custom_profiles[model_name] = profile
        self._save_custom()

    def _load_custom(self):
        if self._profile_path.exists():
            try:
                self._custom_profiles = json.loads(self._profile_path.read_text())
            except Exception:
                self._custom_profiles = {}

    def _save_custom(self):
        self._profile_path.write_text(json.dumps(self._custom_profiles, indent=2))
