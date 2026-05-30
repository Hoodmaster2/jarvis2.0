"""
Hybrid long-term memory with SQLite metadata + vector search via Ollama embeddings.
"""
import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MEMORY_TYPES = [
    "preference", "project", "task", "tool_usage",
    "coding_fix", "website_note", "automation", "skill_behavior",
    "suggestion", "episodic", "procedural", "conversation",
]


class HybridMemory:
    def __init__(self, db_path: str = "./data/hybrid_memory.db", embed_fn=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._embed = embed_fn
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        c = self._conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                project TEXT DEFAULT '',
                embedding TEXT,
                importance INTEGER DEFAULT 1,
                access_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_type ON memory_entries(memory_type);
            CREATE INDEX IF NOT EXISTS idx_project ON memory_entries(project);
            CREATE INDEX IF NOT EXISTS idx_created ON memory_entries(created_at);
        """)

    def _embed_text(self, text: str) -> list[float]:
        if self._embed:
            try:
                return self._embed(text)
            except Exception as e:
                logger.warning(f"Embedding failed: {e}")
        return []

    def add(self, memory_type: str, content: str, metadata: dict = None,
            project: str = "", importance: int = 1) -> dict:
        if memory_type not in MEMORY_TYPES:
            memory_type = "task"
        entry_id = str(uuid.uuid4())[:12]
        now = datetime.utcnow().isoformat()
        meta_json = json.dumps(metadata or {})
        embedding = self._embed_text(content)
        embedding_json = json.dumps(embedding) if embedding else "[]"

        self._conn.execute(
            """INSERT INTO memory_entries
               (id, memory_type, content, metadata, project, embedding, importance, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, memory_type, content, meta_json, project, embedding_json, importance, now, now),
        )
        self._conn.commit()
        return {"id": entry_id, "type": memory_type, "content": content, "created_at": now}

    def search(self, query: str, memory_type: str = None, project: str = None,
               limit: int = 20) -> list[dict]:
        q_embedding = self._embed_text(query)

        if q_embedding:
            entries = self._get_all_filtered(memory_type, project)
            scored = []
            for e in entries:
                e_emb = json.loads(e["embedding"]) if e.get("embedding") else []
                if e_emb:
                    score = self._cosine_similarity(q_embedding, e_emb)
                    scored.append((score, e))
            scored.sort(key=lambda x: -x[0])
            results = [self._row_to_dict(e) for _, e in scored[:limit]]
            for r in results:
                r["score"] = round(scored[results.index(r)][0], 4) if results.index(r) < len(scored) else 0
        else:
            like = f"%{query}%"
            rows = self._conn.execute(
                """SELECT *, 0 as score FROM memory_entries
                   WHERE content LIKE ? {type_filter} {project_filter}
                   ORDER BY created_at DESC LIMIT ?""".format(
                    type_filter="AND memory_type=?" if memory_type else "",
                    project_filter="AND project=?" if project else "",
                ),
                [like] + ([memory_type] if memory_type else []) + ([project] if project else []) + [limit],
            ).fetchall()
            results = [self._row_to_dict(r) for r in rows]

        return results

    def semantic_search(self, query: str, memory_type: str = None, limit: int = 20) -> list[dict]:
        return self.search(query, memory_type=memory_type, limit=limit)

    def get_by_type(self, memory_type: str, project: str = None, limit: int = 50) -> list[dict]:
        if project:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE memory_type=? AND project=? ORDER BY created_at DESC LIMIT ?",
                (memory_type, project, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE memory_type=? ORDER BY created_at DESC LIMIT ?",
                (memory_type, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_by_project(self, project: str, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM memory_entries WHERE project=? ORDER BY created_at DESC LIMIT ?",
            (project, limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_timeline(self, days: int = 7, memory_type: str = None, limit: int = 100) -> list[dict]:
        from datetime import timedelta
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        if memory_type:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE created_at>? AND memory_type=? ORDER BY created_at DESC LIMIT ?",
                (since, memory_type, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE created_at>? ORDER BY created_at DESC LIMIT ?",
                (since, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, entry_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM memory_entries WHERE id=?", (entry_id,)
        ).fetchone()
        if row:
            self._conn.execute(
                "UPDATE memory_entries SET access_count=access_count+1 WHERE id=?", (entry_id,)
            )
            self._conn.commit()
            return self._row_to_dict(row)
        return None

    def update(self, entry_id: str, content: str = None, metadata: dict = None,
               importance: int = None) -> bool:
        existing = self.get(entry_id)
        if not existing:
            return False
        now = datetime.utcnow().isoformat()
        if content:
            embedding = self._embed_text(content)
            self._conn.execute(
                "UPDATE memory_entries SET content=?, embedding=?, updated_at=? WHERE id=?",
                (content, json.dumps(embedding), now, entry_id),
            )
        if metadata:
            self._conn.execute(
                "UPDATE memory_entries SET metadata=?, updated_at=? WHERE id=?",
                (json.dumps(metadata), now, entry_id),
            )
        if importance is not None:
            self._conn.execute(
                "UPDATE memory_entries SET importance=?, updated_at=? WHERE id=?",
                (importance, now, entry_id),
            )
        self._conn.commit()
        return True

    def delete(self, entry_id: str) -> bool:
        c = self._conn.execute("DELETE FROM memory_entries WHERE id=?", (entry_id,))
        self._conn.commit()
        return c.rowcount > 0

    def clear(self, memory_type: str = None):
        if memory_type:
            self._conn.execute("DELETE FROM memory_entries WHERE memory_type=?", (memory_type,))
        else:
            self._conn.execute("DELETE FROM memory_entries")
        self._conn.commit()

    def count(self, memory_type: str = None) -> int:
        if memory_type:
            row = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM memory_entries WHERE memory_type=?", (memory_type,)
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) as cnt FROM memory_entries").fetchone()
        return row["cnt"] if row else 0

    def get_projects(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT project FROM memory_entries WHERE project!='' ORDER BY project"
        ).fetchall()
        return [r["project"] for r in rows]

    def export(self, memory_type: str = None, project: str = None) -> list[dict]:
        if memory_type and project:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE memory_type=? AND project=? ORDER BY created_at",
                (memory_type, project),
            ).fetchall()
        elif memory_type:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE memory_type=? ORDER BY created_at",
                (memory_type,),
            ).fetchall()
        elif project:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE project=? ORDER BY created_at",
                (project,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries ORDER BY created_at"
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def import_entries(self, entries: list[dict]):
        for e in entries:
            self.add(
                memory_type=e.get("memory_type", "task"),
                content=e.get("content", ""),
                metadata=json.loads(e.get("metadata", "{}")),
                project=e.get("project", ""),
                importance=e.get("importance", 1),
            )

    def cleanup_old(self, days: int = 90):
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        self._conn.execute("DELETE FROM memory_entries WHERE created_at<? AND importance<3", (cutoff,))
        self._conn.commit()

    def _get_all_filtered(self, memory_type: str = None, project: str = None) -> list[dict]:
        if memory_type and project:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE memory_type=? AND project=?", (memory_type, project)
            ).fetchall()
        elif memory_type:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE memory_type=?", (memory_type,)
            ).fetchall()
        elif project:
            rows = self._conn.execute(
                "SELECT * FROM memory_entries WHERE project=?", (project,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM memory_entries").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        import math
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if not na or not nb:
            return 0
        return dot / (na * nb)

    def _row_to_dict(self, row) -> dict:
        return {
            "id": row["id"],
            "type": row["memory_type"],
            "content": row["content"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "project": row["project"],
            "importance": row["importance"],
            "access_count": row["access_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def close(self):
        self._conn.close()
