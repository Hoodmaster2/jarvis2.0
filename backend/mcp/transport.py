import asyncio
import json
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class MCPServerProcess:
    def __init__(self, command: str, args: list = None, env: dict = None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._process: Optional[asyncio.subprocess.Process] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def start(self):
        full_env = {**__import__('os').environ, **self.env}
        self._process = await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
        )
        self._reader = self._process.stdout
        logger.info(f"MCP process started: {self.command} (pid={self._process.pid})")

    async def read_line(self) -> Optional[str]:
        if self._reader:
            line = await self._reader.readline()
            return line.decode("utf-8", errors="replace").strip() if line else None
        return None

    async def write_line(self, data: str):
        if self._process and self._process.stdin:
            self._process.stdin.write((data + "\n").encode("utf-8"))
            await self._process.stdin.drain()

    async def stop(self):
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            logger.info(f"MCP process stopped: {self.command}")

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.returncode is None


class MCPStdioTransport:
    def __init__(self, command: str, args: list = None, env: dict = None):
        self.server = MCPServerProcess(command, args, env)
        self._pending: dict = {}

    async def connect(self):
        await self.server.start()
        return True

    async def disconnect(self):
        await self.server.stop()

    async def send_request(self, method: str, params: dict = None, request_id: str = None) -> dict:
        msg = {"jsonrpc": "2.0", "id": request_id or __import__('uuid').uuid4().hex[:8], "method": method}
        if params:
            msg["params"] = params
        msg_str = json.dumps(msg)
        logger.debug(f"MCP send: {msg_str[:200]}")
        await self.server.write_line(msg_str)
        response_line = await self.server.read_line()
        if response_line:
            try:
                return json.loads(response_line)
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON response: {response_line[:200]}"}
        return {"error": "No response from MCP server"}

    @property
    def connected(self) -> bool:
        return self.server.running


class MCPWebSocketTransport:
    def __init__(self, url: str):
        self.url = url
        self._ws = None

    async def connect(self):
        try:
            import websockets
            self._ws = await websockets.connect(self.url)
            logger.info(f"MCP WebSocket connected: {self.url}")
            return True
        except ImportError:
            logger.error("websockets package not installed")
            return False
        except Exception as e:
            logger.error(f"MCP WebSocket connection failed: {e}")
            return False

    async def disconnect(self):
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def send_request(self, method: str, params: dict = None, request_id: str = None) -> dict:
        import uuid
        msg = {"jsonrpc": "2.0", "id": request_id or uuid.uuid4().hex[:8], "method": method}
        if params:
            msg["params"] = params
        await self._ws.send(json.dumps(msg))
        response = await self._ws.recv()
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON: {response[:200]}"}

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._ws.open
