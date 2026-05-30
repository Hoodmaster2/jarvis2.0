import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from .schemas import MCPServerConfig
from .registry import get_mcp_registry

logger = logging.getLogger(__name__)


CONFIG_DIRS = [
    Path.home() / ".config" / "mcp",
    Path.home() / ".mcp",
    Path.cwd() / ".mcp",
]


def discover_local_servers() -> List[MCPServerConfig]:
    found = []
    for cfg_dir in CONFIG_DIRS:
        if cfg_dir.exists():
            for f in cfg_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    configs = data if isinstance(data, list) else [data]
                    for c in configs:
                        found.append(MCPServerConfig(
                            name=c.get("name", f.stem),
                            command=c.get("command", ""),
                            args=c.get("args", []),
                            url=c.get("url", ""),
                            transport=c.get("transport", "stdio"),
                            env=c.get("env", {}),
                            trusted=c.get("trusted", False),
                        ))
                except Exception as e:
                    logger.warning(f"Failed to load MCP config {f}: {e}")
    return found


COMMON_MCP_SERVERS = {
    "playwright": MCPServerConfig(
        name="playwright",
        command="npx",
        args=["@playwright/mcp"],
        transport="stdio",
        description="Browser automation via Playwright",
    ),
    "filesystem": MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["@modelcontextprotocol/server-filesystem"],
        transport="stdio",
        description="Filesystem operations",
    ),
    "github": MCPServerConfig(
        name="github",
        command="npx",
        args=["@modelcontextprotocol/server-github"],
        transport="stdio",
        description="GitHub API integration",
    ),
    "git": MCPServerConfig(
        name="git",
        command="npx",
        args=["@modelcontextprotocol/server-git"],
        transport="stdio",
        description="Git repository operations",
    ),
}


class MCPDiscovery:
    def __init__(self, registry=None):
        self.registry = registry or get_mcp_registry()

    def scan_config_dirs(self) -> list:
        configs = discover_local_servers()
        for cfg in configs:
            if not self.registry.get_server(cfg.name):
                self.registry.add_server(cfg)
        return [cfg.name for cfg in configs]

    def suggest_common_servers(self) -> dict:
        result = {}
        for name, config in COMMON_MCP_SERVERS.items():
            exists = self.registry.get_server(name)
            result[name] = {
                "config": config.to_dict(),
                "registered": exists is not None,
                "connected": exists.connected if exists else False,
            }
        return result

    async def register_and_connect(self, config: MCPServerConfig) -> dict:
        if self.registry.get_server(config.name):
            return {"status": "already_registered", "name": config.name}
        client = self.registry.add_server(config)
        ok = await client.connect()
        return {
            "status": "connected" if ok else "failed",
            "name": config.name,
            "tools": [t.to_dict() for t in client.tools] if ok else [],
            "error": client._error if not ok else "",
        }
