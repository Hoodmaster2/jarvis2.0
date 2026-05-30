import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

DEFAULT_WORKSPACE_DIR = Path.home() / ".jarvis" / "workspaces"


class WorkspaceManager:
    def __init__(self, workspace_dir: str = None):
        self._workspace_dir = Path(workspace_dir) if workspace_dir else DEFAULT_WORKSPACE_DIR
        self._workspace_dir.mkdir(parents=True, exist_ok=True)
        self._workspaces: dict = {}
        self._load_workspaces()

    def _load_workspaces(self):
        index_file = self._workspace_dir / "workspaces.json"
        if index_file.exists():
            try:
                self._workspaces = json.loads(index_file.read_text(encoding="utf-8"))
            except Exception:
                self._workspaces = {}

    def _save_workspaces(self):
        index_file = self._workspace_dir / "workspaces.json"
        try:
            index_file.write_text(json.dumps(self._workspaces, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save workspaces: {e}")

    def create_workspace(self, name: str, path: str, description: str = "") -> dict:
        wid = str(uuid4())
        workspace = {
            "id": wid,
            "name": name,
            "path": path,
            "description": description,
            "created_at": time.time(),
            "last_opened": time.time(),
            "tags": [],
        }
        self._workspaces[wid] = workspace
        self._save_workspaces()
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[dict]:
        return self._workspaces.get(workspace_id)

    def list_workspaces(self) -> list:
        return sorted(self._workspaces.values(), key=lambda w: w.get("last_opened", 0), reverse=True)

    def update_workspace(self, workspace_id: str, updates: dict) -> bool:
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return False
        ws.update(updates)
        ws["last_opened"] = time.time()
        self._save_workspaces()
        return True

    def delete_workspace(self, workspace_id: str) -> bool:
        ok = self._workspaces.pop(workspace_id, None) is not None
        if ok:
            self._save_workspaces()
        return ok

    def add_tag(self, workspace_id: str, tag: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return False
        if tag not in ws.setdefault("tags", []):
            ws["tags"].append(tag)
            self._save_workspaces()
        return True
