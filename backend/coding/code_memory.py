import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CodeMemory:
    def __init__(self):
        self._repos: Dict[str, dict] = {}
        self._fixes: List[dict] = []
        self._architectures: Dict[str, str] = {}
        self._max_fixes = 200

    def store_repo_summary(self, path: str, summary: str, languages: list):
        self._repos[path] = {
            "path": path,
            "summary": summary,
            "languages": languages,
            "stored_at": time.time(),
        }

    def get_repo_summary(self, path: str) -> Optional[dict]:
        return self._repos.get(path)

    def list_repos(self) -> list:
        return list(self._repos.values())

    def store_fix(self, path: str, error: str, fix: str, success: bool = True):
        entry = {
            "path": path,
            "error": error[:500],
            "fix": fix[:1000],
            "success": success,
            "timestamp": time.time(),
        }
        self._fixes.append(entry)
        if len(self._fixes) > self._max_fixes:
            self._fixes = self._fixes[-self._max_fixes:]

    def search_fixes(self, query: str, limit: int = 10) -> list:
        query_lower = query.lower()
        results = []
        for f in reversed(self._fixes):
            if query_lower in f["error"].lower() or query_lower in f["fix"].lower():
                results.append(f)
                if len(results) >= limit:
                    break
        return results

    def store_architecture(self, path: str, description: str):
        self._architectures[path] = description

    def get_architecture(self, path: str) -> Optional[str]:
        return self._architectures.get(path)

    def get_stats(self) -> dict:
        return {
            "repos": len(self._repos),
            "fixes": len(self._fixes),
            "architectures": len(self._architectures),
        }
