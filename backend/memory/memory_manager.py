"""
SQLite-based memory system with vector search support.
Stores conversations, preferences, notes, and agent logs.
"""
import json
import sqlite3
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MemoryManager:
    """Persistent memory using SQLite with optional vector embeddings."""

    def __init__(self, db_path: str = "./data/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self._conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                embedding BLOB,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tools_used TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS skills_registry (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                enabled INTEGER DEFAULT 1,
                manifest TEXT NOT NULL,
                installed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
            CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
        """)
        self._conn.commit()

    def add_memory(self, type: str, content: str, metadata: dict = None, embedding: list = None):
        """Store a memory entry."""
        mem_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "INSERT INTO memories (id, type, content, metadata, embedding, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (mem_id, type, content, json.dumps(metadata or {}),
             json.dumps(embedding) if embedding else None, now, now),
        )
        self._conn.commit()
        return mem_id

    def search_memories(self, query: str, type: str = None, limit: int = 20) -> list:
        """Search memories by content (basic text search)."""
        cursor = self._conn.cursor()
        like = f"%{query}%"
        if type:
            cursor.execute(
                "SELECT * FROM memories WHERE content LIKE ? AND type = ? ORDER BY created_at DESC LIMIT ?",
                (like, type, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM memories WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (like, limit),
            )
        return [dict(row) for row in cursor.fetchall()]

    def get_memories_by_type(self, type: str, limit: int = 50) -> list:
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM memories WHERE type = ? ORDER BY created_at DESC LIMIT ?",
            (type, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all_memories(self, limit: int = 100) -> list:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def delete_memory(self, mem_id: str) -> bool:
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_memories_by_type(self, type: str) -> int:
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM memories WHERE type = ?", (type,))
        self._conn.commit()
        return cursor.rowcount

    def clear_all_memories(self):
        self._conn.execute("DELETE FROM memories")
        self._conn.commit()

    def add_conversation(self, session_id: str, role: str, content: str, tools_used: list = None):
        conv_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "INSERT INTO conversations (id, session_id, role, content, tools_used, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (conv_id, session_id, role, content, json.dumps(tools_used or []), now),
        )
        self._conn.commit()

    def get_conversation_history(self, session_id: str, limit: int = 50) -> list:
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM conversations WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def set_preference(self, key: str, value: str):
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO user_preferences (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, now),
        )
        self._conn.commit()

    def get_preference(self, key: str, default=None) -> Optional[str]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

    def get_all_preferences(self) -> dict:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM user_preferences")
        return {row["key"]: row["value"] for row in cursor.fetchall()}

    def register_skill(self, name: str, manifest: dict, enabled: bool = True):
        now = datetime.utcnow().isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO skills_registry (id, name, enabled, manifest, installed_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), name, 1 if enabled else 0, json.dumps(manifest), now),
        )

    def get_skill(self, name: str) -> Optional[dict]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM skills_registry WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_skills(self) -> list:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM skills_registry ORDER BY installed_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def set_skill_enabled(self, name: str, enabled: bool):
        self._conn.execute(
            "UPDATE skills_registry SET enabled = ? WHERE name = ?",
            (1 if enabled else 0, name),
        )
        self._conn.commit()

    def export_memories(self, filepath: str):
        """Export all memories to JSON file."""
        import json
        memories = self.get_all_memories(limit=10000)
        with open(filepath, "w") as f:
            json.dump(memories, f, indent=2)

    def close(self):
        self._conn.close()
