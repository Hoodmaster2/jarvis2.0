"""
Failure analyzer - stores failure reasons and suggests avoidances.
"""
import json
import logging
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FailureAnalyzer:
    def __init__(self, storage_path: str = "./data/learning/failures.json"):
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._failures: list[dict] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self._failures = json.loads(self.path.read_text())
            except Exception:
                self._failures = []

    def _save(self):
        self.path.write_text(json.dumps(self._failures, indent=2))

    def record_failure(self, action: str, tool: str, error: str, context: str = "",
                       task_id: str = ""):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "action": action,
            "tool": tool,
            "error": error,
            "context": context,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "avoided": False,
        }
        self._failures.append(entry)
        self._save()
        return entry

    def mark_avoided(self, failure_id: str):
        for f in self._failures:
            if f["id"] == failure_id:
                f["avoided"] = True
                f["avoided_at"] = datetime.utcnow().isoformat()
                self._save()
                return True
        return False

    def get_patterns(self) -> list[dict]:
        if not self._failures:
            return []
        action_tools = Counter((f["action"], f["tool"]) for f in self._failures if not f.get("avoided"))
        error_msgs = Counter(f["error"][:100] for f in self._failures if not f.get("avoided"))
        return [
            {"type": "frequent_action_tool", "items": [
                {"action": a, "tool": t, "count": c} for (a, t), c in action_tools.most_common(10)
            ]},
            {"type": "common_errors", "items": [
                {"error": e, "count": c} for e, c in error_msgs.most_common(10)
            ]},
        ]

    def get_avoidance_suggestions(self) -> list[str]:
        patterns = self.get_patterns()
        suggestions = []
        for p in patterns:
            if p["type"] == "frequent_action_tool":
                for item in p["items"][:3]:
                    suggestions.append(
                        f"Avoid using {item['tool']} for {item['action']} "
                        f"(failed {item['count']} times)"
                    )
        return suggestions

    def get_all(self, limit: int = 100) -> list[dict]:
        return self._failures[-limit:]

    def clear(self):
        self._failures = []
        self._save()
