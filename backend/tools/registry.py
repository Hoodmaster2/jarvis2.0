import logging
from typing import Any, Callable, Dict, Optional
from .schemas import ToolSchema, ToolAction, ToolParameter, PermissionLevel

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._schemas: Dict[str, ToolSchema] = {}
        self._handlers: Dict[str, Dict[str, Callable]] = {}

    def register_tool(self, schema: ToolSchema, handler: Callable):
        self._schemas[schema.tool_name] = schema
        self._handlers[schema.tool_name] = {"*": handler}
        logger.info(f"Registered tool: {schema.tool_name} ({len(schema.actions)} actions)")

    def register_action(self, tool_name: str, action_name: str, handler: Callable):
        if tool_name not in self._handlers:
            self._handlers[tool_name] = {}
        self._handlers[tool_name][action_name] = handler

    def get_schema(self, tool_name: str) -> Optional[ToolSchema]:
        return self._schemas.get(tool_name)

    def get_all_schemas(self) -> list:
        return [s.to_dict() for s in self._schemas.values()]

    def get_handler(self, tool_name: str, action_name: str = "*") -> Optional[Callable]:
        handlers = self._handlers.get(tool_name, {})
        handler = handlers.get(action_name) or handlers.get("*")
        return handler

    def get_permission_level(self, tool_name: str, action_name: str) -> PermissionLevel:
        schema = self.get_schema(tool_name)
        if schema:
            return schema.get_permission_level(action_name)
        return PermissionLevel.HIGH

    def get_permission_reason(self, tool_name: str, action_name: str) -> str:
        schema = self.get_schema(tool_name)
        if schema:
            action = schema.get_action(action_name)
            if action and action.permission_reason:
                return action.permission_reason
        return f"Execute {tool_name}.{action_name}"

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._schemas

    def unregister_tool(self, tool_name: str):
        self._schemas.pop(tool_name, None)
        self._handlers.pop(tool_name, None)


_registry = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def tool_schema(
    tool_name: str,
    description: str = "",
    actions: list = None,
    default_permission: str = "safe",
):
    def decorator(func):
        schema = ToolSchema(
            tool_name=tool_name,
            description=description or func.__doc__ or "",
            actions=[
                ToolAction(
                    name=a.get("name", "run"),
                    description=a.get("description", ""),
                    parameters=[
                        ToolParameter(**p) if isinstance(p, dict) else p
                        for p in a.get("parameters", [])
                    ],
                    permission_level=PermissionLevel(a.get("permission_level", default_permission)),
                    permission_reason=a.get("permission_reason", ""),
                )
                for a in (actions or [])
            ],
            default_permission=PermissionLevel(default_permission),
        )
        registry = get_registry()
        registry.register_tool(schema, func)
        return func
    return decorator
