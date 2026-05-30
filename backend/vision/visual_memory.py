import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class VisualMemory:
    def __init__(self):
        self._entries: List[dict] = []
        self._max_entries = 200

    def store(self, image_path: str, summary: str, metadata: dict = None) -> str:
        vid = str(uuid4())
        entry = {
            "id": vid,
            "image_path": image_path,
            "summary": summary,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        return vid

    def search_by_text(self, query: str, limit: int = 10) -> List[dict]:
        query_lower = query.lower()
        results = []
        for entry in reversed(self._entries):
            if query_lower in entry["summary"].lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        return results

    def search_by_metadata(self, key: str, value: str) -> List[dict]:
        return [e for e in reversed(self._entries) if e.get("metadata", {}).get(key) == value]

    def get_recent(self, limit: int = 20) -> List[dict]:
        return [{
            "id": e["id"],
            "image_path": e["image_path"],
            "summary": e["summary"][:200],
            "timestamp": e["timestamp"],
        } for e in self._entries[-limit:]]

    def get(self, visual_id: str) -> Optional[dict]:
        for e in self._entries:
            if e["id"] == visual_id:
                return e
        return None

    def delete(self, visual_id: str) -> bool:
        for i, e in enumerate(self._entries):
            if e["id"] == visual_id:
                self._entries.pop(i)
                return True
        return False

    def clear(self):
        self._entries.clear()

    def get_stats(self) -> dict:
        return {
            "total": len(self._entries),
            "recent_hours": sum(1 for e in self._entries if time.time() - e["timestamp"] < 3600),
        }
