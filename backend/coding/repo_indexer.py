import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", "dist", "build", ".next", ".nuxt"}
CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".json", ".md",
             ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bat", ".ps1", ".sql",
             ".rs", ".go", ".java", ".cpp", ".c", ".h", ".hpp", ".rb", ".php", ".swift"}


class RepoIndexer:
    def __init__(self):
        self._indexes: dict = {}

    def index_project(self, path: str, recursive: bool = True, max_files: int = 2000) -> dict:
        p = Path(path)
        if not p.exists():
            return {"error": f"Path not found: {path}"}
        if str(p) in self._indexes:
            return self._indexes[str(p)]

        index = {
            "name": p.name,
            "path": str(p.absolute()),
            "files": [],
            "dirs": [],
            "languages": {},
            "total_size": 0,
            "total_lines": 0,
            "file_count": 0,
            "dir_count": 0,
            "indexed_at": time.time(),
            "has_git": (p / ".git").exists(),
            "git_branch": "",
        }
        self._walk(p, index, recursive, max_files)
        if index["has_git"]:
            try:
                import git
                repo = git.Repo(p)
                index["git_branch"] = str(repo.active_branch)
            except Exception:
                pass

        self._indexes[str(p)] = index
        logger.info(f"Indexed {path}: {index['file_count']} files, {len(index['languages'])} languages")
        return index

    def _walk(self, path: Path, index: dict, recursive: bool, max_files: int):
        if index["file_count"] >= max_files:
            return
        try:
            for item in path.iterdir():
                if item.name.startswith(".") or item.name in IGNORE_DIRS:
                    continue
                if item.is_dir():
                    if recursive:
                        index["dirs"].append(str(item.relative_to(Path(index["path"]))))
                        index["dir_count"] += 1
                        self._walk(item, index, recursive, max_files)
                elif item.is_file():
                    ext = item.suffix.lower()
                    if ext in CODE_EXTS:
                        try:
                            content = item.read_text(encoding="utf-8", errors="replace")
                            lines = content.count("\n")
                            index["files"].append({
                                "path": str(item.relative_to(Path(index["path"]))),
                                "name": item.name,
                                "ext": ext,
                                "size": len(content),
                                "lines": lines,
                                "modified": item.stat().st_mtime,
                            })
                            index["languages"][ext] = index["languages"].get(ext, 0) + 1
                            index["total_size"] += len(content)
                            index["total_lines"] += lines
                            index["file_count"] += 1
                        except (PermissionError, OSError, UnicodeDecodeError):
                            pass
        except PermissionError:
            pass

    def get_index(self, path: str) -> Optional[dict]:
        return self._indexes.get(str(Path(path)))

    def list_indexed_projects(self) -> list:
        return [{"name": v["name"], "path": v["path"], "files": v["file_count"], "languages": list(v["languages"].keys())}
                for v in self._indexes.values()]

    def get_file_content(self, path: str, file_rel_path: str) -> Optional[str]:
        p = Path(path) / file_rel_path
        if p.exists() and p.is_file():
            try:
                return p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return None
        return None

    def remove_index(self, path: str):
        key = str(Path(path))
        self._indexes.pop(key, None)
