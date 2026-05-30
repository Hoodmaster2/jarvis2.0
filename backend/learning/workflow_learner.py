"""
Workflow learner - detects repeated patterns and suggests automations.
"""
import json
import logging
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkflowLearner:
    def __init__(self, storage_path: str = "./data/learning/workflows.json"):
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._workflows: list[dict] = []
        self._patterns: list[dict] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._workflows = data.get("workflows", [])
                self._patterns = data.get("patterns", [])
            except Exception:
                pass

    def _save(self):
        self.path.write_text(json.dumps({
            "workflows": self._workflows[-500:],
            "patterns": self._patterns,
        }, indent=2))

    def record_workflow(self, steps: list[dict], source: str = "", user_id: str = ""):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "steps": steps,
            "source": source,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "completed": all(s.get("status") == "success" for s in steps),
        }
        self._workflows.append(entry)
        self._analyze_patterns()
        self._save()
        return entry

    def _analyze_patterns(self):
        action_sequences = defaultdict(int)
        for wf in self._workflows[-200:]:
            actions = tuple(s.get("action", "") for s in wf.get("steps", []))
            if len(actions) >= 2:
                action_sequences[actions] += 1

        self._patterns = [
            {
                "id": str(uuid.uuid4())[:8],
                "sequence": list(seq),
                "frequency": count,
                "last_observed": self._get_last_observed(seq),
                "type": self._classify_pattern(list(seq)),
            }
            for seq, count in action_sequences.items()
            if count >= 2
        ]
        self._patterns.sort(key=lambda p: -p["frequency"])

    def _get_last_observed(self, sequence: tuple) -> str:
        for wf in reversed(self._workflows):
            actions = tuple(s.get("action", "") for s in wf.get("steps", []))
            if actions == sequence:
                return wf["timestamp"]
        return ""

    def _classify_pattern(self, actions: list[str]) -> str:
        action_set = set(actions)
        if {"goto", "click", "fill"}.intersection(action_set):
            return "browser"
        if {"git_commit", "git_push", "code_edit"}.intersection(action_set):
            return "coding"
        if {"launch_app", "type_text", "hotkey"}.intersection(action_set):
            return "desktop"
        if {"search", "summarize", "extract"}.intersection(action_set):
            return "research"
        return "general"

    def get_repeatable_patterns(self, min_frequency: int = 2) -> list[dict]:
        return [p for p in self._patterns if p["frequency"] >= min_frequency]

    def suggest_automations(self) -> list[dict]:
        suggestions = []
        for pattern in self._patterns:
            if pattern["frequency"] >= 3 and pattern["type"] != "general":
                suggestions.append({
                    "id": pattern["id"],
                    "sequence": pattern["sequence"],
                    "frequency": pattern["frequency"],
                    "type": pattern["type"],
                    "suggestion": f"Found {pattern['type']} workflow repeated {pattern['frequency']}x. "
                                  f"Create automation?",
                })
        return suggestions[:10]

    def get_recent(self, limit: int = 50) -> list[dict]:
        return self._workflows[-limit:]

    def get_stats(self) -> dict:
        total = len(self._workflows)
        completed = sum(1 for w in self._workflows if w.get("completed"))
        types = Counter(w.get("source", "unknown") for w in self._workflows)
        return {
            "total_workflows": total,
            "completed": completed,
            "failed": total - completed,
            "by_source": dict(types.most_common(10)),
            "patterns_found": len(self._patterns),
        }

    def clear(self):
        self._workflows = []
        self._patterns = []
        self._save()
