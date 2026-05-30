import logging
from typing import Any, Dict, Optional

from tools.registry import get_registry, ToolRegistry
from tools.schemas import ToolSchema, ToolAction, ToolParameter, PermissionLevel
from .registry import get_mcp_registry
from .permissions import get_mcp_permission_manager

logger = logging.getLogger(__name__)


class MCPToolAdapter:
    def __init__(self, tool_registry: ToolRegistry = None):
        self.tool_registry = tool_registry or get_registry()

    def register_mcp_tools(self, server_name: str, tools: list) -> int:
        count = 0
        for tool in tools:
            self._register_single_tool(server_name, tool)
            count += 1
        logger.info(f"Registered {count} MCP tools from {server_name}")
        return count

    def _register_single_tool(self, server_name: str, tool):
        tool_name = tool.get("name", "unknown")
        description = tool.get("description", "")
        params = tool.get("parameters", {})
        properties = params.get("properties", {})

        tool_display_name = f"mcp_{server_name}_{tool_name}"
        schema = ToolSchema(
            tool_name=tool_display_name,
            description=f"MCP {server_name}: {description}",
            actions=[
                ToolAction(
                    name="call",
                    description=description,
                    parameters=[
                        ToolParameter(
                            name=k,
                            type=v.get("type", "string"),
                            description=v.get("description", ""),
                            required=k in (params.get("required", [])),
                        )
                        for k, v in properties.items()
                    ],
                    permission_level=PermissionLevel.HIGH,
                    permission_reason=f"MCP tool from server '{server_name}'",
                )
            ],
        )

        async def handler(tool_name=None, action=None, args=None):
            mcp_registry = get_mcp_registry()
            client = mcp_registry.get_server(server_name)
            if not client or not client.connected:
                return {"error": f"MCP server '{server_name}' not connected"}
            perm_mgr = get_mcp_permission_manager()
            allowed, reason = perm_mgr.can_execute(server_name, tool_name)
            if not allowed:
                return {"error": f"Permission denied: {reason}"}
            result = await client.call_tool(tool_name, args or {})
            return result

        self.tool_registry.register_tool(schema, handler)

    def unregister_mcp_tools(self, server_name: str):
        schema_key = f"mcp_{server_name}"
        self.tool_registry.unregister_tool(schema_key)
        logger.info(f"Unregistered MCP tools from {server_name}")

    def sync_registered_tools(self, server_name: str) -> int:
        mcp_registry = get_mcp_registry()
        client = mcp_registry.get_server(server_name)
        if not client:
            return 0
        self.unregister_mcp_tools(server_name)
        tool_dicts = [t.to_dict() for t in client.tools]
        return self.register_mcp_tools(server_name, tool_dicts)
