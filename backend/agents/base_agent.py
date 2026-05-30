"""
Base agent class for the multi-agent architecture.
Extends the original BaseAgent from orchestrator.py with message bus integration,
lifecycle management, and standardized task execution.
"""
import json
import logging
import time
import uuid
from enum import Enum
from typing import Any, AsyncGenerator, Optional

from ollama_client import OllamaClient
from memory.memory_manager import MemoryManager
from security.permissions import PermissionManager
from skills_engine.skill_manager import SkillManager
from agents.message_bus import MessageBus, Message, MessageType
from models.router import ModelRouter

logger = logging.getLogger(__name__)


class AgentState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    FAILED = "failed"
    COMPLETED = "completed"


class BaseAgent:
    """Abstract base for all specialized agents in the multi-agent system."""

    def __init__(
        self,
        name: str,
        ollama: OllamaClient,
        memory: MemoryManager,
        permissions: PermissionManager,
        skills: SkillManager,
        message_bus: MessageBus,
        model_router: ModelRouter,
        system_prompt: str = "",
    ):
        self.name = name
        self.ollama = ollama
        self.memory = memory
        self.permissions = permissions
        self.skills = skills
        self.bus = message_bus
        self.router = model_router
        self.session_id = str(uuid.uuid4())
        self.system_prompt = system_prompt or self._default_prompt()
        self.state = AgentState.IDLE
        self._current_task_id = None
        self._observations: list[dict] = []
        self._last_error = None

        # Subscribe to the message bus
        self.bus.subscribe(self.name, self._handle_message)

    def _default_prompt(self) -> str:
        return f"""You are {self.name}, a specialized agent in the JARVIS multi-agent system.
You communicate with other agents via structured messages.
You use tools to accomplish tasks assigned to you.
Always report observations and results clearly.
Current session: {self.session_id}"""

    def get_model(self) -> str:
        """Get the assigned model for this agent."""
        return self.router.get_model_for(self.name)

    async def _handle_message(self, message: Message):
        """Handle incoming messages from the bus."""
        if message.type == MessageType.COORDINATOR_COMMAND:
            await self._handle_command(message)
        elif message.type == MessageType.TASK_ASSIGN:
            await self._handle_task(message)
        elif message.type == MessageType.REQUEST_APPROVAL:
            await self._handle_approval_request(message)

    async def _handle_command(self, message: Message):
        """Handle a coordinator command."""
        action = message.payload.get("action")
        if action == "shutdown":
            self.state = AgentState.COMPLETED
        elif action == "reset":
            self.state = AgentState.IDLE
            self._observations = []
            self._last_error = None

    async def _handle_task(self, message: Message):
        """Handle an assigned task. Override in subclasses."""
        self.state = AgentState.EXECUTING
        self._current_task_id = message.correlation_id
        try:
            result = await self.execute_task(message.payload)
            await self.bus.publish(Message(
                msg_type=MessageType.TASK_RESULT,
                sender=self.name,
                recipient=message.sender,
                payload={"task_id": message.correlation_id, "result": result},
                correlation_id=message.id,
            ))
            self.state = AgentState.IDLE
        except Exception as e:
            self.state = AgentState.FAILED
            self._last_error = str(e)
            await self.bus.publish(Message(
                msg_type=MessageType.ERROR,
                sender=self.name,
                recipient=message.sender,
                payload={"task_id": message.correlation_id, "error": str(e)},
                correlation_id=message.id,
            ))

    async def _handle_approval_request(self, message: Message):
        """Handle an approval request."""
        logger.info(f"{self.name} received approval request: {message.payload}")

    async def execute_task(self, task_data: dict) -> Any:
        """Execute a task. Override in subclasses."""
        raise NotImplementedError

    async def think(self, prompt: str, tools: list = None, temperature: float = 0.7) -> str:
        """Have the agent think using its LLM."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        result = await self.ollama.chat(messages, tools=tools, temperature=temperature)
        content = result.get("message", {}).get("content", "")
        return content

    async def think_stream(self, prompt: str, tools: list = None) -> AsyncGenerator[dict, None]:
        """Stream thinking output."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        async for chunk in self.ollama.chat_stream(messages, tools=tools):
            yield chunk

    async def observe(self, observation: dict):
        """Record an observation."""
        self._observations.append({
            "timestamp": time.time(),
            "agent": self.name,
            "observation": observation,
        })
        # Share with bus for other agents
        await self.bus.publish(Message(
            msg_type=MessageType.OBSERVATION,
            sender=self.name,
            recipient="*",
            payload={"agent": self.name, "observation": observation},
        ))

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "model": self.get_model(),
            "session_id": self.session_id,
            "current_task": self._current_task_id,
            "observations_count": len(self._observations),
            "last_error": self._last_error,
        }

    async def cleanup(self):
        """Cleanup resources."""
        self.bus.unsubscribe(self.name)
