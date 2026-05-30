"""
Prompt optimizer - learns from successful/failed prompts and improves.
"""
import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptOptimizer:
    def __init__(self, storage_path: str = "./data/learning/prompts.json"):
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._history: list[dict] = []
        self._templates: dict[str, str] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._history = data.get("history", [])
                self._templates = data.get("templates", {})
            except Exception:
                pass

    def _save(self):
        self.path.write_text(json.dumps({
            "history": self._history[-500:],
            "templates": self._templates,
        }, indent=2))

    def record_prompt(self, prompt: str, context: str = "", task_type: str = "",
                      outcome: str = "unknown", response_quality: float = 0.5):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "prompt": prompt,
            "context": context,
            "task_type": task_type,
            "outcome": outcome,
            "response_quality": response_quality,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._history.append(entry)
        self._save()
        return entry

    def get_best_prompts(self, task_type: str = "", limit: int = 5) -> list[dict]:
        candidates = [h for h in self._history if h["outcome"] == "success"]
        if task_type:
            candidates = [h for h in candidates if h["task_type"] == task_type]
        candidates.sort(key=lambda h: -h["response_quality"])
        return candidates[:limit]

    def optimize_prompt(self, prompt: str, task_type: str = "") -> str:
        best = self.get_best_prompts(task_type)
        if not best:
            return prompt

        improvements = []
        for b in best[:3]:
            if b["response_quality"] > 0.8 and len(b["prompt"]) > len(prompt) * 0.5:
                improvements.append(b["prompt"])

        if improvements:
            best_parts = []
            for imp in improvements:
                lines = [l.strip() for l in imp.split("\n") if l.strip()]
                for line in lines:
                    if line.lower().startswith(("you are", "your role", "you have", "you should")):
                        if line not in best_parts:
                            best_parts.append(line)
            if best_parts:
                return "\n".join(best_parts) + "\n\n" + prompt

        return prompt

    def save_template(self, name: str, template: str):
        self._templates[name] = template
        self._save()

    def get_template(self, name: str) -> str:
        return self._templates.get(name, "")

    def get_all_templates(self) -> dict:
        return dict(self._templates)

    def get_stats(self) -> dict:
        total = len(self._history)
        succeeded = sum(1 for h in self._history if h["outcome"] == "success")
        failed = sum(1 for h in self._history if h["outcome"] == "failed")
        return {
            "total_prompts": total,
            "succeeded": succeeded,
            "failed": failed,
            "success_rate": round(succeeded / total, 2) if total else 0,
            "templates": len(self._templates),
        }

    def clear(self):
        self._history = []
        self._templates = {}
        self._save()
