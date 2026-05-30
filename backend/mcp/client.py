import asyncio
import json
import logging
from typing import Any, Optional

from .schemas import MCPServerConfig, MCPTool, MCPConnectionStatus
from .transport import MCPStdioTransport, MCPWebSocketTransport

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.status = MCPConnectionStatus.DISCONNECTED
        self._transport = None
        self._tools: list[MCPTool] = []
        self._error = ""

    async def connect(self):
        if self.status == MCPConnectionStatus.CONNECTED:
            return True
        self.status = MCPConnectionStatus.CONNECTING
        try:
            if self.config.transport == "stdio":
                self._transport = MCPStdioTransport(self.config.command, self.config.args, self.config.env)
            elif self.config.transport == "websocket":
                self._transport = MCPWebSocketTransport(self.config.url)
            else:
                self._error = f"Unknown transport: {self.config.transport}"
                self.status = MCPConnectionStatus.ERROR
                return False
            ok = await self._transport.connect()
            if ok:
                self.status = MCPConnectionStatus.CONNECTED
                await self._initialize()
                return True
            else:
                self._error = "Transport connection failed"
                self.status = MCPConnectionStatus.ERROR
                return False
        except Exception as e:
            self._error = str(e)
            self.status = MCPConnectionStatus.ERROR
            logger.error(f"MCP connect failed for {self.config.name}: {e}")
            return False

    async def _initialize(self):
        resp = await self._transport.send_request("initialize", {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {"name": "jarvis", "version": "1.0.0"},
        })
        if "error" in resp:
            self._error = resp["error"]
        resp2 = await self._transport.send_request("notifications/initialized")
        await self._discover_tools()

    async def _discover_tools(self):
        resp = await self._transport.send_request("tools/list")
        if "error" in resp:
            self._error = resp["error"]
            return
        result = resp.get("result", resp)
        raw_tools = result if isinstance(result, list) else result.get("tools", [])
        self._tools = []
        for t in raw_tools:
            params = t.get("inputSchema", t.get("parameters", {}))
            self._tools.append(MCPTool(
                name=t.get("name", "unknown"),
                description=t.get("description", ""),
                parameters=params,
                server_name=self.config.name,
            ))

    async def call_tool(self, tool_name: str, args: dict = None) -> dict:
        if self.status != MCPConnectionStatus.CONNECTED:
            return {"error": "Not connected"}
        resp = await self._transport.send_request("tools/call", {
            "name": tool_name,
            "arguments": args or {},
        })
        result = resp.get("result", resp)
        if isinstance(result, dict) and "content" in result:
            return result
        return {"result": result}

    @property
    def tools(self) -> list[MCPTool]:
        return self._tools

    @property
    def connected(self) -> bool:
        return self.status == MCPConnectionStatus.CONNECTED

    async def disconnect(self):
        if self._transport:
            await self._transport.disconnect()
        self.status = MCPConnectionStatus.DISCONNECTED
        self._tools = []

    def to_dict(self) -> dict:
        return {
            "name": self.config.name,
            "status": self.status.value,
            "transport": self.config.transport,
            "tools": [t.to_dict() for t in self._tools],
            "error": self._error,
            "trusted": self.config.trusted,
            "config": self.config.to_dict(),
        }
