from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
import time


class MCPConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPTool:
    name: str
    description: str = ""
    parameters: dict = field(default_factory=dict)
    server_name: str = ""
    enabled: bool = True
    permission_level: str = "safe"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "server_name": self.server_name,
            "enabled": self.enabled,
            "permission_level": self.permission_level,
        }


@dataclass
class MCPMessage:
    jsonrpc: str = "2.0"
    id: str = field(default_factory=lambda: str(uuid4()))
    method: str = ""
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"jsonrpc": self.jsonrpc, "id": self.id, "method": self.method, "params": self.params}


@dataclass
class MCPServerConfig:
    name: str
    command: str = ""
    args: list = field(default_factory=list)
    url: str = ""
    transport: str = "stdio"
    env: dict = field(default_factory=dict)
    trusted: bool = False
    auto_start: bool = False
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "url": self.url,
            "transport": self.transport,
            "env_keys": list(self.env.keys()),
            "trusted": self.trusted,
            "auto_start": self.auto_start,
            "created_at": self.created_at,
        }
