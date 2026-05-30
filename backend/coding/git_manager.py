import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GitManager:
    def __init__(self):
        self._repos: dict = {}

    def _get_repo(self, path: str):
        import git
        p = Path(path)
        if not (p / ".git").exists():
            return None
        if path not in self._repos:
            self._repos[path] = git.Repo(p)
        return self._repos[path]

    def get_status(self, path: str) -> dict:
        repo = self._get_repo(path)
        if not repo:
            return {"error": "Not a git repository"}
        try:
            return {
                "branch": str(repo.active_branch),
                "modified": [item.a_path for item in repo.index.diff(None)],
                "staged": [item.a_path for item in repo.index.diff("HEAD")],
                "untracked": repo.untracked_files,
                "ahead": sum(1 for _ in repo.iter_commits(f"origin/{repo.active_branch}..{repo.active_branch}"))
                if f"origin/{repo.active_branch}" in repo.refs else 0,
                "behind": sum(1 for _ in repo.iter_commits(f"{repo.active_branch}..origin/{repo.active_branch}"))
                if f"origin/{repo.active_branch}" in repo.refs else 0,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_log(self, path: str, max_count: int = 20) -> list:
        repo = self._get_repo(path)
        if not repo:
            return []
        commits = []
        for commit in repo.iter_commits(max_count=max_count):
            commits.append({
                "hash": commit.hexsha[:8],
                "author": str(commit.author),
                "message": commit.message.strip(),
                "date": commit.committed_datetime.isoformat(),
            })
        return commits

    def get_diff(self, path: str, target: str = "HEAD") -> str:
        repo = self._get_repo(path)
        if not repo:
            return "Not a git repository"
        try:
            diff = repo.git.diff(target)
            return diff
        except Exception as e:
            return str(e)

    def create_commit(self, path: str, message: str, author: str = "JARVIS") -> dict:
        repo = self._get_repo(path)
        if not repo:
            return {"error": "Not a git repository"}
        try:
            repo.index.add("*")
            repo.index.commit(message, author=author)
            return {"status": "committed", "message": message}
        except Exception as e:
            return {"error": str(e)}

    def create_branch(self, path: str, branch_name: str) -> dict:
        repo = self._get_repo(path)
        if not repo:
            return {"error": "Not a git repository"}
        try:
            current = repo.active_branch
            repo.git.checkout("-b", branch_name)
            return {"status": "created", "branch": branch_name}
        except Exception as e:
            return {"error": str(e)}

    def checkout(self, path: str, branch: str) -> dict:
        repo = self._get_repo(path)
        if not repo:
            return {"error": "Not a git repository"}
        try:
            repo.git.checkout(branch)
            return {"status": "checked_out", "branch": branch}
        except Exception as e:
            return {"error": str(e)}

    def stash(self, path: str, message: str = "") -> dict:
        repo = self._get_repo(path)
        if not repo:
            return {"error": "Not a git repository"}
        try:
            repo.git.stash("push", "-m", message or f"stash {time.time()}")
            return {"status": "stashed"}
        except Exception as e:
            return {"error": str(e)}

    def get_branches(self, path: str) -> list:
        repo = self._get_repo(path)
        if not repo:
            return []
        return [str(b) for b in repo.branches]

    def close(self, path: str):
        self._repos.pop(path, None)
