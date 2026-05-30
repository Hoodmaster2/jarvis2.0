"""
Browser task memory - stores actions, replays, session logs for browser workflows.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MEMORY_DIR = Path("./data/browser_tasks")


class BrowserTaskMemory:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._actions_file = MEMORY_DIR / "actions.jsonl"
        self._sessions_file = MEMORY_DIR / "sessions.json"

    def log_action(self, session_id: str, action: str, params: dict, result: dict):
        entry = {
            "id": str(uuid.uuid4())[:8],
            "session_id": session_id,
            "action": action,
            "params": params,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        with open(self._actions_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def get_action_history(self, session_id: str = None, limit: int = 100) -> list[dict]:
        if not self._actions_file.exists():
            return []
        entries = []
        with open(self._actions_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if session_id and entry["session_id"] != session_id:
                    continue
                entries.append(entry)
        return entries[-limit:]

    def save_session_meta(self, session_id: str, meta: dict):
        data = {}
        if self._sessions_file.exists():
            data = json.loads(self._sessions_file.read_text())
        data[session_id] = {**meta, "updated_at": datetime.utcnow().isoformat()}
        self._sessions_file.write_text(json.dumps(data, indent=2))

    def get_login_sessions(self) -> list[dict]:
        if not self._sessions_file.exists():
            return []
        data = json.loads(self._sessions_file.read_text())
        return [
            {"session_id": sid, **meta}
            for sid, meta in data.items()
            if meta.get("type") == "login"
        ]

    def get_replay_actions(self, session_id: str) -> list[dict]:
        return [
            entry for entry in self.get_action_history(session_id)
            if entry["action"] in ("goto", "click", "fill", "submit")
        ]

    def clear_history(self, session_id: str = None):
        if session_id:
            entries = self.get_action_history()
            entries = [e for e in entries if e["session_id"] != session_id]
            with open(self._actions_file, "w") as f:
                for e in entries:
                    f.write(json.dumps(e) + "\n")
        else:
            self._actions_file.write_text("")
            self._sessions_file.write_text("{}")
