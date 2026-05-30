import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class MCPPermissionManager:
    def __init__(self):
        self._trusted_servers: set = set()
        self._server_scopes: dict = {}
        self._blocked_tools: set = set()
        self._require_approval: bool = True

    def trust_server(self, name: str):
        self._trusted_servers.add(name)

    def untrust_server(self, name: str):
        self._trusted_servers.discard(name)

    def is_trusted(self, name: str) -> bool:
        return name in self._trusted_servers

    def set_server_scope(self, server_name: str, scopes: list):
        self._server_scopes[server_name] = scopes

    def get_server_scope(self, server_name: str) -> list:
        return self._server_scopes.get(server_name, [])

    def block_tool(self, tool_name: str):
        self._blocked_tools.add(tool_name)

    def unblock_tool(self, tool_name: str):
        self._blocked_tools.discard(tool_name)

    def is_tool_blocked(self, tool_name: str) -> bool:
        return tool_name in self._blocked_tools

    def can_execute(self, server_name: str, tool_name: str) -> tuple:
        if self.is_tool_blocked(tool_name):
            return False, "Tool is blocked"
        if self.is_trusted(server_name):
            return True, ""
        if self._require_approval:
            return False, "Server is not trusted - requires approval"
        return True, ""

    def set_require_approval(self, required: bool):
        self._require_approval = required


_permission_manager = None


def get_mcp_permission_manager() -> MCPPermissionManager:
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = MCPPermissionManager()
    return _permission_manager
