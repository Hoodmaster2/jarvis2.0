"""
Memory Search skill for JARVIS.
Queries the SQLite memory database.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# This skill expects the memory_manager to be passed in by the orchestrator
_memory = None


def set_memory(memory_manager):
    global _memory
    _memory = memory_manager


async def execute(command: str, **kwargs) -> dict:
    commands = {
        "query": cmd_query,
        "recent": cmd_recent,
        "preferences": cmd_preferences,
    }
    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return await handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


def _get_memory():
    if _memory is None:
        try:
            from memory.memory_manager import MemoryManager
            from config import Config
            cfg = Config()
            global _memory
            _memory = MemoryManager(cfg.memory_path)
        except Exception as e:
            logger.error(f"Cannot init memory: {e}")
            return None
    return _memory


async def cmd_query(query: str, type: str = None, limit: int = 10) -> dict:
    mem = _get_memory()
    if not mem:
        return {"error": "Memory not available"}
    results = mem.search_memories(query, type, limit)
    return {"results": results, "count": len(results)}


async def cmd_recent(limit: int = 10) -> dict:
    mem = _get_memory()
    if not mem:
        return {"error": "Memory not available"}
    results = mem.get_all_memories(limit)
    return {"results": results, "count": len(results)}


async def cmd_preferences() -> dict:
    mem = _get_memory()
    if not mem:
        return {"error": "Memory not available"}
    prefs = mem.get_all_preferences()
    return {"preferences": prefs}
