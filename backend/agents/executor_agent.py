"""
Executor Agent - executes approved tool calls, runs skills, returns observations, handles retries.
"""
import asyncio
import json
import logging
from typing import Any

from agents.base_agent import BaseAgent
from agents.message_bus import Message, MessageType

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM_PROMPT = """You are JARVIS Executor Agent. Your role is to:
1. Execute tool calls and skill commands safely
2. Handle retries when operations fail
3. Return clear observations from executed actions
4. Respect permission boundaries - never bypass security

You have access to all installed JARVIS skills through the execute_tool action.
Always report the exact result of each operation."""


class ExecutorAgent(BaseAgent):
    """Executes tool calls and skill commands."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = EXECUTOR_SYSTEM_PROMPT
        self._execution_history: list[dict] = []
        self._max_retries = 2

    async def execute_task(self, task_data: dict) -> Any:
        action = task_data.get("action", "execute_tool")
        if action == "execute_tool":
            return await self._execute_tool_task(task_data)
        elif action == "execute_batch":
            return await self._execute_batch(task_data.get("steps", []))
        return {"error": f"Unknown action: {action}"}

    async def _execute_tool_task(self, task_data: dict) -> dict:
        """Execute a tool/skill call with retry logic."""
        request = task_data.get("request", "")
        tool_hint = task_data.get("tool_hint", "")
        tool_name = task_data.get("tool_name", "")
        tool_args = task_data.get("tool_args", {})

        # If we have specific tool info, use it directly
        if tool_name and tool_args:
            return await self._execute_with_retry(tool_name, tool_args)

        # Otherwise, ask the LLM to determine the right tool
        return await self._determine_and_execute(request, tool_hint)

    async def _determine_and_execute(self, request: str, tool_hint: str) -> dict:
        """Ask the LLM which tool to use, then execute it."""
        available_skills = self.skills.get_all_skills()
        skills_desc = "\n".join(
            f"- {s['name']}: {s['description']} (commands: {[c.get('name') for c in s.get('commands', [])]})"
            for s in available_skills
        )

        prompt = f"""Determine which tool/skill to use for this request and with what parameters.

Request: {request}
Tool hint: {tool_hint}

Available skills:
{skills_desc}

Output JSON:
{{"skill": "skill_name", "command": "command_name", "args": {{...}}}}"""

        content = await self.think(prompt)

        import re
        json_match = re.search(r'\{[\s\S]*"skill"[\s\S]*\}', content)
        if json_match:
            try:
                decision = json.loads(json_match.group())
                return await self._execute_with_retry(
                    f"skill_{decision['skill']}_{decision['command']}",
                    decision.get("args", {}),
                )
            except (json.JSONDecodeError, KeyError):
                pass

        return {"error": "Could not determine tool", "raw_response": content[:500]}

    async def _execute_with_retry(self, tool_name: str, args: dict) -> dict:
        """Execute a tool with retry logic."""
        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                # Parse tool name: skill_<name>_<command>
                if tool_name.startswith("skill_"):
                    parts = tool_name.split("_", 2)
                    if len(parts) >= 3:
                        skill_name = parts[1]
                        command = parts[2]
                        result = await self.skills.execute_command(skill_name, command, **args)
                    else:
                        result = {"error": f"Invalid tool name: {tool_name}"}
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                # Check for permission requirements
                if isinstance(result, dict) and result.get("status") == "needs_approval":
                    # Request approval via bus
                    approval = await self._request_approval(result)
                    if approval:
                        continue  # Retry after approval
                    return {"status": "denied", "reason": "User denied permission"}

                self._execution_history.append({
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                    "attempt": attempt,
                    "success": "error" not in result,
                })
                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Tool execution attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1 * (attempt + 1))

        return {"error": f"Failed after {self._max_retries + 1} retries: {last_error}"}

    async def _request_approval(self, action_info: dict) -> bool:
        """Request user approval via the bus."""
        msg = Message(
            msg_type=MessageType.REQUEST_APPROVAL,
            sender=self.name,
            recipient="coordinator",
            payload=action_info,
        )
        response = await self.bus.request(msg, timeout=60.0)
        if response:
            return response.payload.get("approved", False)
        return False

    async def _execute_batch(self, steps: list[dict]) -> list[dict]:
        """Execute multiple tool calls in sequence."""
        results = []
        for step in steps:
            result = await self._execute_with_retry(
                step.get("tool_name", ""),
                step.get("args", {}),
            )
            results.append(result)
        return results

    def get_execution_history(self, limit: int = 20) -> list[dict]:
        return self._execution_history[-limit:]
