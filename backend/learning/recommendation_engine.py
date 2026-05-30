"""
Recommendation engine - suggests skills, workflows, and automations based on usage.
"""
import json
import logging
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class RecommendationEngine:
    def __init__(self, storage_path: str = "./data/learning/recommendations.json"):
        self.path = Path(storage_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._usage_log: list[dict] = []
        self._recommendations: list[dict] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._usage_log = data.get("usage_log", [])
                self._recommendations = data.get("recommendations", [])
            except Exception:
                pass

    def _save(self):
        self.path.write_text(json.dumps({
            "usage_log": self._usage_log[-1000:],
            "recommendations": self._recommendations,
        }, indent=2))

    def log_usage(self, category: str, item: str, context: str = ""):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "category": category,
            "item": item,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._usage_log.append(entry)
        self._generate_recommendations()
        self._save()
        return entry

    def _generate_recommendations(self):
        skill_usage = Counter(
            e["item"] for e in self._usage_log if e["category"] == "skill"
        )
        tool_usage = Counter(
            e["item"] for e in self._usage_log if e["category"] == "tool"
        )
        task_types = Counter(
            e["context"] for e in self._usage_log if e["category"] == "task"
        )

        recommendations = []
        if skill_usage:
            top_skill, top_count = skill_usage.most_common(1)[0]
            if top_count > 5:
                recommendations.append({
                    "id": str(uuid.uuid4())[:8],
                    "type": "skill_promotion",
                    "message": f"You frequently use '{top_skill}'. Consider creating a dedicated workflow.",
                    "confidence": min(top_count / 20, 1.0),
                    "source": "usage_pattern",
                })

        if len(tool_usage) > 3:
            rec = {
                "id": str(uuid.uuid4())[:8],
                "type": "tool_diversity",
                "message": "You're using multiple tools - consider creating automation macros.",
                "confidence": 0.6,
                "source": "tool_diversity",
            }
            recommendations.append(rec)

        if task_types:
            most_common = task_types.most_common(3)
            contexts = [c for c, _ in most_common]
            rec = {
                "id": str(uuid.uuid4())[:8],
                "type": "task_pattern",
                "message": f"Common tasks: {', '.join(contexts)}. "
                           f"Create skill shortcuts?",
                "confidence": 0.7,
                "source": "task_frequency",
            }
            recommendations.append(rec)

        self._recommendations = recommendations

    def get_recommendations(self, min_confidence: float = 0.3) -> list[dict]:
        return [
            r for r in self._recommendations
            if r.get("confidence", 0) >= min_confidence
        ]

    def dismiss(self, rec_id: str):
        self._recommendations = [r for r in self._recommendations if r["id"] != rec_id]
        self._save()

    def get_usage_stats(self) -> dict:
        categories = Counter(e["category"] for e in self._usage_log)
        return {
            "total_events": len(self._usage_log),
            "by_category": dict(categories),
            "top_skills": [
                {"name": n, "count": c}
                for n, c in Counter(
                    e["item"] for e in self._usage_log if e["category"] == "skill"
                ).most_common(5)
            ],
            "top_tools": [
                {"name": n, "count": c}
                for n, c in Counter(
                    e["item"] for e in self._usage_log if e["category"] == "tool"
                ).most_common(5)
            ],
        }

    def clear(self):
        self._usage_log = []
        self._recommendations = []
        self._save()
