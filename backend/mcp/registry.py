import logging
from typing import Dict, List, Optional

from .schemas import MCPServerConfig, MCPTool
from .client import MCPClient

logger = logging.getLogger(__name__)


class MCPRegistry:
    def __init__(self):
        self._servers: Dict[str, MCPClient] = {}
        self._trusted_servers: set = set()

    def add_server(self, config: MCPServerConfig) -> MCPClient:
        client = MCPClient(config)
        self._servers[config.name] = client
        if config.trusted:
            self._trusted_servers.add(config.name)
        logger.info(f"MCP server registered: {config.name}")
        return client

    def remove_server(self, name: str) -> bool:
        if name in self._servers:
            import asyncio
            try:
                asyncio.create_task(self._servers[name].disconnect())
            except Exception:
                pass
            del self._servers[name]
            self._trusted_servers.discard(name)
            return True
        return False

    def get_server(self, name: str) -> Optional[MCPClient]:
        return self._servers.get(name)

    def get_all_servers(self) -> list:
        return [c.to_dict() for c in self._servers.values()]

    def get_all_tools(self) -> list[MCPTool]:
        tools = []
        for client in self._servers.values():
            if client.connected:
                tools.extend(client.tools)
        return tools

    def is_trusted(self, server_name: str) -> bool:
        return server_name in self._trusted_servers

    def trust_server(self, name: str):
        self._trusted_servers.add(name)
        if name in self._servers:
            self._servers[name].config.trusted = True

    def untrust_server(self, name: str):
        self._trusted_servers.discard(name)
        if name in self._servers:
            self._servers[name].config.trusted = False

    async def connect_all(self):
        for name, client in self._servers.items():
            if client.config.auto_start:
                await client.connect()

    async def shutdown_all(self):
        for name, client in list(self._servers.items()):
            await client.disconnect()


_registry = None


def get_mcp_registry() -> MCPRegistry:
    global _registry
    if _registry is None:
        _registry = MCPRegistry()
    return _registry
