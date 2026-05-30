"""
Memory Agent - manages contextual memory, retrieves relevant information, summarizes context,
and prevents duplicated work across agents.
"""
import json
import logging
import time
from typing import Any, Optional

from agents.base_agent import BaseAgent
from agents.message_bus import Message, MessageType

logger = logging.getLogger(__name__)

MEMORY_SYSTEM_PROMPT = """You are JARVIS Memory Agent. Your role is to:
1. Retrieve relevant context from past interactions
2. Summarize long conversations and documents
3. Detect duplicate information across agent work
4. Store important observations and results
5. Provide semantically relevant context to other agents

You help prevent duplicated work and ensure agents have the context they need."""


class MemoryAgent(BaseAgent):
    """Manages shared context and semantic memory for the multi-agent system."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = MEMORY_SYSTEM_PROMPT
        self._session_summaries: dict[str, str] = {}

    async def execute_task(self, task_data: dict) -> Any:
        action = task_data.get("action", "retrieve_context")
        handlers = {
            "retrieve_context": self._retrieve_context,
            "store_result": self._store_result,
            "summarize": self._summarize,
            "check_duplicate": self._check_duplicate,
            "get_agent_context": self._get_agent_context,
            "save_workflow_state": self._save_workflow_state,
        }
        handler = handlers.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(task_data)

    async def _retrieve_context(self, task_data: dict) -> dict:
        """Retrieve relevant context for a request."""
        query = task_data.get("query", "")
        limit = task_data.get("limit", 5)

        # Search vector memory
        vector_results = []
        if hasattr(self, 'vector_memory') and self.vector_memory:
            vector_results = self.vector_memory.search(query, k=limit)

        # Search SQLite memory
        sql_results = self.memory.search_memories(query, limit=limit)

        # Get recent conversations
        conversations = self.memory.get_conversation_history(
            task_data.get("session_id", self.session_id), limit=10
        )

        # Summarize context
        context = self._build_context(vector_results, sql_results, conversations)
        return {"context": context, "sources": {"vector": len(vector_results), "sql": len(sql_results), "conversations": len(conversations)}}

    def _build_context(self, vector_results: list, sql_results: list, conversations: list) -> str:
        """Build a context summary from multiple sources."""
        parts = []

        if vector_results:
            parts.append("--- Semantic Memory ---")
            for r in vector_results[:3]:
                parts.append(f"- {r.get('text', '')[:200]}")
                parts.append("")

        if sql_results:
            parts.append("--- Stored Memories ---")
            for r in sql_results[:3]:
                parts.append(f"[{r.get('type', 'unknown')}] {r.get('content', '')[:200]}")

        if conversations:
            parts.append("--- Recent Conversation ---")
            for c in conversations[-4:]:
                parts.append(f"{c.get('role', '?')}: {c.get('content', '')[:150]}")

        return "\n".join(parts) if parts else "No relevant context found."

    async def _store_result(self, task_data: dict) -> dict:
        """Store a result in memory."""
        content = task_data.get("content", "")
        source = task_data.get("source", "agent")
        mem_type = task_data.get("type", "agent_result")
        metadata = task_data.get("metadata", {})

        # Add to vector memory
        vec_id = None
        if hasattr(self, 'vector_memory') and self.vector_memory:
            vec_id = self.vector_memory.add(content, {"source": source, **metadata}, namespace="agent_results")

        # Add to SQLite
        sql_id = self.memory.add_memory(mem_type, content, {"source": source, **metadata})

        await self.observe({"type": "stored", "source": source, "vector_id": vec_id, "sql_id": sql_id})
        return {"status": "stored", "vector_id": vec_id, "sql_id": sql_id}

    async def _summarize(self, task_data: dict) -> dict:
        """Summarize content for shorter context windows."""
        content = task_data.get("content", "")
        max_length = task_data.get("max_length", 500)

        if len(content) <= max_length:
            return {"summary": content, "truncated": False}

        prompt = f"""Summarize the following content in {max_length} characters or less. Keep key facts and actionable information:

{content[:5000]}"""

        summary = await self.think(prompt)
        return {"summary": summary[:max_length], "truncated": len(summary) > max_length, "original_length": len(content)}

    async def _check_duplicate(self, task_data: dict) -> dict:
        """Check if work has already been done on this topic."""
        query = task_data.get("query", "")

        vector_results = []
        if hasattr(self, 'vector_memory') and self.vector_memory:
            vector_results = self.vector_memory.search(query, k=3, namespace="agent_results")

        sql_results = self.memory.search_memories(query, limit=3)

        has_duplicate = len(vector_results) > 0 or len(sql_results) > 0
        return {
            "has_duplicate": has_duplicate,
            "existing_results": vector_results[:2] + sql_results[:2],
            "suggestion": "Use existing results" if has_duplicate else "Proceed with new work",
        }

    async def _get_agent_context(self, task_data: dict) -> dict:
        """Get context specifically for an agent."""
        agent_name = task_data.get("agent_name", "")
        task_type = task_data.get("task_type", "")

        query = f"{agent_name} {task_type}"
        results = self.memory.search_memories(query, type="agent_result", limit=5)
        return {"agent": agent_name, "context": [r.get("content", "") for r in results]}

    async def _save_workflow_state(self, task_data: dict) -> dict:
        """Save the current state of a workflow."""
        graph_id = task_data.get("graph_id", "")
        state = task_data.get("state", {})
        self.memory.add_memory(
            "workflow_state",
            json.dumps(state),
            {"graph_id": graph_id, "timestamp": time.time()},
        )
        return {"status": "saved", "graph_id": graph_id}

    def get_session_summary(self, session_id: str) -> Optional[str]:
        return self._session_summaries.get(session_id)
