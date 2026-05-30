import asyncio
import logging
from typing import Dict, List, Optional

from .schemas import MCPServerConfig, MCPConnectionStatus
from .registry import get_mcp_registry
from .discovery import MCPDiscovery
from .adapters import MCPToolAdapter
from .permissions import get_mcp_permission_manager

logger = logging.getLogger(__name__)


class MCPServerManager:
    def __init__(self):
        self.registry = get_mcp_registry()
        self.discovery = MCPDiscovery(self.registry)
        self.adapter = MCPToolAdapter()
        self.permissions = get_mcp_permission_manager()
        self._connection_tasks: dict = {}

    async def start(self):
        discovered = self.discovery.scan_config_dirs()
        if discovered:
            logger.info(f"Discovered MCP servers: {discovered}")
        await self.registry.connect_all()
        for server in self.registry.get_all_servers():
            if server["status"] == "connected":
                client = self.registry.get_server(server["name"])
                if client:
                    self.adapter.sync_registered_tools(server["name"])
        logger.info("MCP Server Manager started")

    async def stop(self):
        for task in self._connection_tasks.values():
            task.cancel()
        await self.registry.shutdown_all()

    async def connect_server(self, name: str) -> dict:
        client = self.registry.get_server(name)
        if not client:
            return {"status": "error", "error": f"Server '{name}' not found"}
        ok = await client.connect()
        if ok:
            tool_dicts = [t.to_dict() for t in client.tools]
            registered = self.adapter.sync_registered_tools(name)
            return {
                "status": "connected",
                "server": client.to_dict(),
                "tools_registered": registered,
            }
        return {"status": "failed", "error": client._error}

    async def disconnect_server(self, name: str) -> bool:
        client = self.registry.get_server(name)
        if not client:
            return False
        self.adapter.unregister_mcp_tools(name)
        await client.disconnect()
        return True

    def add_server_config(self, config: MCPServerConfig) -> dict:
        self.registry.add_server(config)
        return {"status": "added", "name": config.name}

    def remove_server(self, name: str) -> bool:
        self.adapter.unregister_mcp_tools(name)
        return self.registry.remove_server(name)

    def get_server_info(self, name: str) -> Optional[dict]:
        client = self.registry.get_server(name)
        return client.to_dict() if client else None

    def get_all_servers(self) -> list:
        return self.registry.get_all_servers()

    def get_all_mcp_tools(self) -> list:
        return [t.to_dict() for t in self.registry.get_all_tools()]

    def trust_server(self, name: str):
        self.registry.trust_server(name)
        self.permissions.trust_server(name)

    def untrust_server(self, name: str):
        self.registry.untrust_server(name)
        self.permissions.untrust_server(name)
