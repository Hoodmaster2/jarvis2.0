import asyncio
import logging
from typing import Optional

from ollama_client import OllamaClient
from memory.memory_manager import MemoryManager
from memory.vector_memory import VectorMemory
from security.permissions import PermissionManager
from skills_engine.skill_manager import SkillManager
from background.daemon import BackgroundDaemon
from background.notifications import NotificationLevel

logger = logging.getLogger(__name__)

SUGGESTION_PROMPT = """You are JARVIS's background observation agent.
You monitor system state and user patterns to suggest helpful automations.
Be concise. Suggest one specific improvement per response.
Current context:
{context}"""


class BackgroundAgent:
    def __init__(
        self,
        ollama: OllamaClient,
        memory: MemoryManager,
        vector_memory: VectorMemory,
        permissions: PermissionManager,
        skills: SkillManager,
        daemon: BackgroundDaemon,
        model: str = None,
    ):
        self.ollama = ollama
        self.memory = memory
        self.vector_memory = vector_memory
        self.permissions = permissions
        self.skills = skills
        self.daemon = daemon
        self.model = model or ollama.model
        self._suggestion_interval = 3600
        self._last_suggestion = 0.0
        self._running = False
        self._loop_task = None

    async def start(self):
        self._running = True
        self._loop_task = asyncio.create_task(self._background_loop())
        logger.info("Background agent started")

    async def stop(self):
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

    async def _background_loop(self):
        while self._running:
            daemon_status = self.daemon.get_status()
            if daemon_status.get("notifications", {}).get("unread", 0) > 0:
                pass
            await asyncio.sleep(self._suggestion_interval)

    async def generate_suggestion(self) -> Optional[str]:
        try:
            recent_memories = self.memory.get_all_memories(10)
            system_status = self.daemon.get_status()
            context = (
                f"System: CPU/Memory from observers\n"
                f"Scheduled tasks: {len(system_status.get('scheduled_tasks', []))}\n"
                f"Recent activity: {[m.get('content', '')[:80] for m in recent_memories]}\n"
            )
            response = await self.ollama.chat([
                {"role": "system", "content": SUGGESTION_PROMPT.format(context=context)},
                {"role": "user", "content": "Analyze and suggest an automation."},
            ])
            suggestion = response.get("message", {}).get("content", "")
            if suggestion:
                self.memory.add_memory("suggestion", suggestion, {"source": "background_agent"})
            return suggestion
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
            return None
