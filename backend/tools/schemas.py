import json
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


class PermissionLevel(Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolParameter:
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None
    pattern: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"type": self.type, "description": self.description}
        if self.enum:
            d["enum"] = self.enum
        if not self.required:
            d["optional"] = True
        return d


@dataclass
class ToolAction:
    name: str
    description: str = ""
    parameters: List[ToolParameter] = field(default_factory=list)
    permission_level: PermissionLevel = PermissionLevel.SAFE
    permission_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "permission_level": self.permission_level.value,
            "permission_reason": self.permission_reason,
        }


@dataclass
class ToolSchema:
    tool_name: str
    description: str = ""
    actions: List[ToolAction] = field(default_factory=list)
    default_permission: PermissionLevel = PermissionLevel.SAFE

    def get_action(self, name: str) -> Optional[ToolAction]:
        for a in self.actions:
            if a.name == name:
                return a
        return None

    def get_permission_level(self, action_name: str) -> PermissionLevel:
        action = self.get_action(action_name)
        if action:
            return action.permission_level
        return self.default_permission

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
            "default_permission": self.default_permission.value,
        }


def validate_args(schema: ToolSchema, action_name: str, args: dict) -> List[str]:
    errors = []
    action = schema.get_action(action_name)
    if not action:
        return [f"Unknown action '{action_name}' for tool '{schema.tool_name}'"]
    for param in action.parameters:
        if param.required and param.name not in args:
            errors.append(f"Missing required parameter '{param.name}'")
        elif param.name in args:
            val = args[param.name]
            if param.type == "string" and not isinstance(val, str):
                errors.append(f"Parameter '{param.name}' should be string, got {type(val).__name__}")
            elif param.type == "integer" and not isinstance(val, int):
                errors.append(f"Parameter '{param.name}' should be integer, got {type(val).__name__}")
            elif param.type == "number" and not isinstance(val, (int, float)):
                errors.append(f"Parameter '{param.name}' should be number, got {type(val).__name__}")
            elif param.type == "boolean" and not isinstance(val, bool):
                errors.append(f"Parameter '{param.name}' should be boolean, got {type(val).__name__}")
            if param.enum and val not in param.enum:
                errors.append(f"Parameter '{param.name}' must be one of {param.enum}, got '{val}'")
    return errors
