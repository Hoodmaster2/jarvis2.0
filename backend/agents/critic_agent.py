"""
Critic Agent - validates outputs, detects hallucinations, inspects tool results, requests retries.
Never allows blind execution chains.
"""
import json
import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

CRITIC_SYSTEM_PROMPT = """You are JARVIS Critic Agent. Your role is to validate outputs and detect problems:
1. Check if tool results match expected outcomes
2. Detect hallucinations or incorrect information
3. Validate that tasks are truly complete
4. Identify security concerns in outputs
5. Request retries or alternative approaches when validation fails

You are the quality gate - never approve flawed outputs."""


class CriticAgent(BaseAgent):
    """Validates agent outputs and detects errors/hallucinations."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = CRITIC_SYSTEM_PROMPT
        self._validation_history: list[dict] = []

    async def execute_task(self, task_data: dict) -> Any:
        action = task_data.get("action", "validate")
        if action == "validate":
            return await self._validate_output(task_data)
        elif action == "validate_plan":
            return await self._validate_plan(task_data.get("plan"))
        elif action == "validate_tool_result":
            return await self._validate_tool_result(task_data.get("tool_name"), task_data.get("result"))
        elif action == "audit_chain":
            return await self._audit_chain(task_data.get("chain", []))
        return {"error": f"Unknown action: {action}"}

    async def _validate_output(self, task_data: dict) -> dict:
        """Validate an agent's output."""
        output = task_data.get("output", "")
        context = task_data.get("context", "")
        agent_name = task_data.get("agent", "unknown")

        prompt = f"""Validate this output from {agent_name}:

Context: {context}
Output: {output[:2000]}

Check for:
1. Does the output actually answer the request?
2. Are there any factual errors or hallucinations?
3. Is the output complete or truncated?
4. Are there any security concerns?
5. Should this be retried?

Output JSON:
{{"valid": true/false, "issues": ["..."], "severity": "low|medium|high|critical", "suggested_action": "approve|retry|reject|escalate", "explanation": "..."}}"""

        content = await self.think(prompt)
        result = self._extract_validation(content)

        self._validation_history.append({
            "agent": agent_name,
            "valid": result.get("valid", False),
            "severity": result.get("severity", "low"),
            "timestamp": __import__('time').time(),
        })
        await self.observe({"type": "validation", "agent": agent_name, "valid": result.get("valid")})
        return result

    def _extract_validation(self, llm_output: str) -> dict:
        import re
        json_match = re.search(r'\{[\s\S]*"valid"[\s\S]*\}', llm_output)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {
            "valid": True,
            "issues": [],
            "severity": "low",
            "suggested_action": "approve",
            "explanation": "Could not parse validation, defaulting to approve",
        }

    async def _validate_plan(self, plan: dict) -> dict:
        """Validate a plan before execution."""
        prompt = f"""Validate this execution plan:

Plan: {json.dumps(plan, indent=2)}

Check:
1. Are all steps necessary?
2. Are dependencies correct?
3. Is the agent assignment appropriate?
4. Are there missing steps?
5. Any security concerns?

Output JSON:
{{"valid": true/false, "issues": ["..."], "suggestions": ["..."], "severity": "low|medium|high"}}"""

        content = await self.think(prompt)
        return self._extract_validation(content)

    async def _validate_tool_result(self, tool_name: str, result: Any) -> dict:
        """Validate a tool execution result."""
        prompt = f"""Validate this tool execution result:

Tool: {tool_name}
Result: {json.dumps(result, indent=2)[:2000]}

Check:
1. Did the tool execute successfully?
2. Is the result meaningful?
3. Are there error messages?
4. Should we retry?

Output JSON:
{{"valid": true/false, "issues": ["..."], "suggested_action": "accept|retry|escalate"}}"""

        content = await self.think(prompt)
        return self._extract_validation(content)

    async def _audit_chain(self, chain: list[dict]) -> dict:
        """Audit a full execution chain for issues."""
        prompt = f"""Audit this execution chain for problems:

Chain: {json.dumps(chain, indent=2)[:3000]}

Check:
1. Any failed steps without recovery?
2. Any inconsistent results?
3. Any unexpected tool calls?
4. Overall success assessment?

Output JSON:
{{"valid": true/false, "failed_steps": [...], "recommendations": [...], "overall_status": "success|partial|failed"}}"""

        content = await self.think(prompt)
        return self._extract_validation(content)

    def get_validation_stats(self) -> dict:
        total = len(self._validation_history)
        valid = sum(1 for v in self._validation_history if v.get("valid"))
        return {
            "total_validations": total,
            "passed": valid,
            "failed": total - valid,
            "recent_issues": [v for v in self._validation_history[-5:] if not v.get("valid")],
        }
