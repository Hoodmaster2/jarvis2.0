import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from ollama_client import OllamaClient
from memory.memory_manager import MemoryManager
from security.permissions import PermissionManager
from skills_engine.skill_manager import SkillManager
from tools.registry import get_registry, ToolRegistry
from tools.schemas import validate_args, ToolSchema, ToolParameter, PermissionLevel
from tools.sandbox import ToolSandbox

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are JARVIS, a sophisticated local AI assistant for Windows 10.
You are helpful, harmless, and honest. You can perform tasks using tools and skills.

Your capabilities:
- Chat and answer questions
- Manage files and folders
- Control the browser (Playwright)
- Run PowerShell commands (with permission)
- Monitor system resources
- Launch applications
- Search the web
- Write and execute code
- Manage memory and preferences
- Install and manage skills

Rules:
1. Be concise and efficient in your responses.
2. For dangerous actions (delete files, install software, change system settings, send messages), ask for user confirmation first.
3. You can use function calls to interact with tools.
4. When using a tool, explain what you're doing.
5. You have access to skills that extend your capabilities.

Current session: {session_id}
User preferences: {preferences}
Available skills: {skills}"""


class BaseAgent:
    def __init__(
        self,
        name: str,
        ollama: OllamaClient,
        memory: MemoryManager,
        permissions: PermissionManager,
        skills: SkillManager,
        model: str = None,
        tool_registry: Optional[ToolRegistry] = None,
        sandbox: Optional[ToolSandbox] = None,
    ):
        self.name = name
        self.ollama = ollama
        self.memory = memory
        self.permissions = permissions
        self.skills = skills
        self.model = model or ollama.model
        self.session_id = str(uuid.uuid4())
        self.system_prompt = SYSTEM_PROMPT
        self.tool_registry = tool_registry or get_registry()
        self.sandbox = sandbox or ToolSandbox()

    def _build_system_message(self) -> dict:
        prefs = self.memory.get_all_preferences()
        skills_info = self.skills.get_all_skills()
        return {
            "role": "system",
            "content": self.system_prompt.format(
                session_id=self.session_id,
                preferences=json.dumps(prefs, indent=2),
                skills=json.dumps(skills_info, indent=2),
            ),
        }

    def _build_skill_tools(self) -> list:
        tools = []
        for skill in self.skills.get_all_skills():
            for cmd in skill.get("commands", []):
                tools.append({
                    "type": "function",
                    "function": {
                        "name": f"skill_{skill['name']}_{cmd.get('name', 'run')}",
                        "description": cmd.get("description", f"Execute {cmd.get('name', 'run')} from {skill['name']}"),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                k: {"type": v.get("type", "string"), "description": v.get("description", "")}
                                if isinstance(v, dict) else {"type": "string", "description": str(v)}
                                for k, v in cmd.get("parameters", {}).items()
                            },
                            "required": cmd.get("required", []) if isinstance(cmd.get("required"), list) else list(cmd.get("parameters", {}).keys()),
                        },
                    },
                })
        for schema in self.tool_registry.get_all_schemas():
            for action in schema.get("actions", []):
                tool_name = schema["tool_name"]
                action_name = action["name"]
                tools.append({
                    "type": "function",
                    "function": {
                        "name": f"tool_{tool_name}_{action_name}",
                        "description": action.get("description", f"Execute {action_name} from {tool_name}"),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                p["name"]: {"type": p.get("type", "string"), "description": p.get("description", "")}
                                for p in action.get("parameters", [])
                            },
                            "required": [p["name"] for p in action.get("parameters", []) if not p.get("optional")],
                        },
                    },
                })
        return tools

    async def chat_stream(self, user_message: str, history: list = None) -> AsyncGenerator[dict, None]:
        messages = [self._build_system_message()]
        if history:
            messages.extend(history[-20:])
        messages.append({"role": "user", "content": user_message})

        tools = self._build_skill_tools()
        full_response = ""

        async for chunk in self.ollama.chat_stream(messages, tools=tools):
            yield chunk

            if "message" in chunk:
                msg = chunk["message"]
                if "content" in msg and msg["content"]:
                    full_response += msg["content"]

                if "tool_calls" in msg:
                    yield {"type": "tool_calls", "tool_calls": msg["tool_calls"]}
                    for tc in msg["tool_calls"]:
                        func = tc.get("function", {})
                        result = await self._execute_tool(func.get("name", ""), func.get("arguments", "{}"))
                        messages.append({
                            "role": "tool",
                            "content": json.dumps(result),
                            "name": func.get("name", ""),
                        })
                        yield {"type": "tool_result", "name": func.get("name", ""), "result": result}

                    async for chunk2 in self.ollama.chat_stream(messages, tools=tools):
                        yield chunk2

        self.memory.add_conversation(self.session_id, "user", user_message)
        self.memory.add_conversation(self.session_id, "assistant", full_response)

    async def _execute_tool(self, tool_name: str, args_json: str) -> dict:
        try:
            args = json.loads(args_json) if isinstance(args_json, str) else args_json
        except json.JSONDecodeError:
            args = {}

        logger.info(f"Executing tool: {tool_name} with args: {args}")

        if tool_name.startswith("tool_"):
            parts = tool_name.split("_", 2)
            if len(parts) >= 3:
                actual_tool_name = parts[1]
                action_name = parts[2]
                schema = self.tool_registry.get_schema(actual_tool_name)
                if schema:
                    errors = validate_args(schema, action_name, args)
                    if errors:
                        return {"error": "; ".join(errors)}
                    handler = self.tool_registry.get_handler(actual_tool_name, action_name)
                    if handler:
                        return await self.sandbox.execute(handler, actual_tool_name, action_name, args)
                return {"error": f"Schema or handler not found for {actual_tool_name}.{action_name}"}

        if tool_name.startswith("skill_"):
            parts = tool_name.split("_", 2)
            if len(parts) >= 3:
                skill_name = parts[1]
                command = parts[2]
                return await self.skills.execute_command(skill_name, command, **args)

        return {"error": f"Unknown tool: {tool_name}"}


class Orchestrator:
    def __init__(
        self,
        ollama: OllamaClient,
        memory: MemoryManager,
        permissions: PermissionManager,
        skills: SkillManager,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.ollama = ollama
        self.memory = memory
        self.permissions = permissions
        self.skills = skills
        self.tool_registry = tool_registry or get_registry()
        self.general_agent = BaseAgent(
            "General", ollama, memory, permissions, skills,
            tool_registry=self.tool_registry,
        )

    async def chat(self, message: str, history: list = None) -> AsyncGenerator[dict, None]:
        async for chunk in self.general_agent.chat_stream(message, history):
            yield chunk

    def get_status(self) -> dict:
        return {
            "ollama_connected": False,
            "model": self.ollama.model,
            "memory_enabled": self.memory is not None,
            "skills_count": len(self.skills.get_all_skills()),
            "skills_list": self.skills.get_all_skills(),
            "pending_approvals": self.permissions.get_pending(),
            "session_id": self.general_agent.session_id,
        }
