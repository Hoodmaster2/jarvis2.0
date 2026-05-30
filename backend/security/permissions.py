import json
import logging
from pathlib import Path
from enum import Enum
from typing import Callable, Optional

from tools.schemas import PermissionLevel, validate_args
from tools.registry import get_registry

logger = logging.getLogger(__name__)


class PermissionManager:
    def __init__(self, config_path: str = None):
        self.mode = "ask"
        self._confirmation_callback: Optional[Callable] = None
        self._pending_approvals = {}
        self.allowed_commands = []
        self.blocked_commands = []

    def set_confirmation_callback(self, callback: Callable):
        self._confirmation_callback = callback

    def classify_action(self, action_type: str, details: str = "") -> PermissionLevel:
        registry = get_registry()
        if registry.has_tool(action_type):
            return registry.get_permission_level(action_type, details)
        tool_name, _, action_name = action_type.partition(".")
        if registry.has_tool(tool_name):
            return registry.get_permission_level(tool_name, action_name or "run")
        return PermissionLevel.SAFE

    def requires_confirmation(self, action_type: str, details: str = "") -> bool:
        if self.mode == "auto":
            return False
        if self.mode == "strict":
            return True
        level = self.classify_action(action_type, details)
        return level in (PermissionLevel.HIGH, PermissionLevel.CRITICAL)

    async def request_approval(self, action_id: str, action_type: str, details: str, description: str) -> bool:
        if not self.requires_confirmation(action_type, details):
            return True
        if self._confirmation_callback:
            result = await self._confirmation_callback(action_id, action_type, details, description)
            self._pending_approvals[action_id] = result
            return result
        return False

    def approve(self, action_id: str) -> bool:
        if action_id in self._pending_approvals:
            self._pending_approvals[action_id] = True
            return True
        return False

    def deny(self, action_id: str) -> bool:
        if action_id in self._pending_approvals:
            self._pending_approvals[action_id] = False
            return True
        return False

    def get_pending(self) -> list:
        return [
            {"id": k, "approved": v}
            for k, v in self._pending_approvals.items()
            if v is None
        ]

    def get_level_name(self, level: PermissionLevel) -> str:
        return level.value.capitalize()

    def describe_action(self, action_type: str, details: str = "") -> dict:
        level = self.classify_action(action_type, details)
        needs_confirm = self.requires_confirmation(action_type, details)
        return {
            "action": action_type,
            "details": details,
            "level": level.value,
            "needs_confirmation": needs_confirm,
        }
