"""
Correction tracker - learns from user corrections and avoids repeated mistakes.
"""
import json
import logging
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class CorrectionTracker:
    def __init__(self, storage_path: str = "./data/learning/corrections.json"):
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._corrections: list[dict] = []
        self._banned_patterns: list[str] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._corrections = data.get("corrections", [])
                self._banned_patterns = data.get("banned_patterns", [])
            except Exception:
                pass

    def _save(self):
        self.path.write_text(json.dumps({
            "corrections": self._corrections[-500:],
            "banned_patterns": self._banned_patterns,
        }, indent=2))

    def record_correction(self, action: str, correction: str, context: str = ""):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "action": action,
            "correction": correction,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
            "applied": False,
        }
        self._corrections.append(entry)

        if self._should_ban(action, correction):
            self._banned_patterns.append(f"{action}: {correction[:50]}")

        self._save()
        return entry

    def _should_ban(self, action: str, correction: str) -> bool:
        deny_keywords = ["never", "stop", "don't", "do not", "wrong", "incorrect"]
        return any(k in correction.lower() for k in deny_keywords)

    def is_banned(self, action: str, context: str = "") -> bool:
        for pattern in self._banned_patterns:
            if action[:30].lower() in pattern.lower():
                return True
        recent = [c for c in self._corrections[-5:] if c["action"] == action]
        if len(recent) >= 3:
            return True
        return False

    def get_recurring_issues(self) -> list[dict]:
        action_counts = Counter(c["action"] for c in self._corrections)
        return [
            {"action": action, "corrections": count, "last": self._get_last(action)}
            for action, count in action_counts.most_common(10)
            if count >= 2
        ]

    def _get_last(self, action: str) -> str:
        for c in reversed(self._corrections):
            if c["action"] == action:
                return c["timestamp"]
        return ""

    def get_corrections(self, limit: int = 50) -> list[dict]:
        return self._corrections[-limit:]

    def get_banned_patterns(self) -> list[str]:
        return list(self._banned_patterns)

    def clear(self):
        self._corrections = []
        self._banned_patterns = []
        self._save()
