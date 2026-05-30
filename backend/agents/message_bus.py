"""
Agent message bus - decoupled communication between agents.
Enables structured messaging, task routing, and observation sharing.
"""
import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class MessageType(Enum):
    TASK_ASSIGN = "task_assign"
    TASK_RESULT = "task_result"
    TASK_UPDATE = "task_update"
    MEMORY_QUERY = "memory_query"
    MEMORY_RESULT = "memory_result"
    OBSERVATION = "observation"
    REQUEST_APPROVAL = "request_approval"
    APPROVAL_RESULT = "approval_result"
    AGENT_STATUS = "agent_status"
    COORDINATOR_COMMAND = "coordinator_command"
    ERROR = "error"
    LOG = "log"


class Message:
    """Structured message for agent communication."""

    def __init__(
        self,
        msg_type: MessageType,
        sender: str,
        recipient: str,
        payload: dict,
        correlation_id: str = None,
        reply_to: str = None,
    ):
        self.id = str(uuid.uuid4())
        self.type = msg_type
        self.sender = sender
        self.recipient = recipient
        self.payload = payload
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.reply_to = reply_to
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            msg_type=MessageType(data["type"]),
            sender=data["sender"],
            recipient=data["recipient"],
            payload=data["payload"],
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
        )


class MessageBus:
    """Async message bus for agent communication."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[Message] = []
        self._max_history = 1000
        self._lock = asyncio.Lock()

    def subscribe(self, agent_name: str, callback: Callable):
        """Subscribe an agent to receive messages."""
        self._subscribers[agent_name].append(callback)
        logger.debug(f"Agent '{agent_name}' subscribed to message bus")

    def unsubscribe(self, agent_name: str, callback: Callable = None):
        """Unsubscribe an agent."""
        if callback:
            self._subscribers[agent_name].remove(callback)
        else:
            self._subscribers[agent_name] = []

    async def publish(self, message: Message):
        """Publish a message to its recipient."""
        async with self._lock:
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        recipient = message.recipient
        if recipient in self._subscribers:
            for callback in self._subscribers[recipient]:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"Error delivering message to {recipient}: {e}")

        # Also deliver to broadcast subscribers
        if "*" in self._subscribers:
            for callback in self._subscribers["*"]:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"Error in broadcast subscriber: {e}")

        logger.debug(f"Message published: {message.type.value} from {message.sender} to {message.recipient}")

    async def request(self, message: Message, timeout: float = 30.0) -> Optional[Message]:
        """Publish a message and wait for a reply."""
        future = asyncio.get_event_loop().create_future()

        async def reply_handler(reply: Message):
            if reply.correlation_id == message.id and not future.done():
                future.set_result(reply)

        self.subscribe(message.sender, reply_handler)
        await self.publish(message)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Request timed out: {message.type.value} from {message.sender} to {message.recipient}")
            return None
        finally:
            self.unsubscribe(message.sender, reply_handler)

    def get_history(self, limit: int = 50, msg_type: MessageType = None) -> list[dict]:
        """Get recent message history."""
        msgs = self._history
        if msg_type:
            msgs = [m for m in msgs if m.type == msg_type]
        return [m.to_dict() for m in msgs[-limit:]]

    def clear_history(self):
        self._history = []
