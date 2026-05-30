"""
Planner Agent - analyzes requests, breaks into steps, assigns tasks, prioritizes execution.
"""
import json
import logging
import time
import uuid
from typing import Any

from agents.base_agent import BaseAgent
from agents.message_bus import Message, MessageType

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are JARVIS Planner Agent. Your role is to:
1. Analyze user requests and break them into clear, executable steps
2. Assign each step to the appropriate specialized agent
3. Determine task dependencies (what must happen before what)
4. Prioritize tasks for efficient execution

Available agents:
- executor_agent: Executes approved tool calls and skills
- memory_agent: Manages long-term memory and context retrieval
- critic_agent: Validates outputs and detects errors
- research_agent: Web search and information gathering
- coding_agent: Code reading, writing, debugging
- automation_agent: Scheduled and recurring tasks

Output a JSON plan with:
{
  "steps": [{"id": "...", "agent": "...", "action": "...", "params": {...}, "depends_on": [...], "priority": 0}],
  "reasoning": "Why this plan",
  "estimated_complexity": "simple|medium|complex"
}"""


class PlannerAgent(BaseAgent):
    """Analyzes requests and produces execution plans."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = PLANNER_SYSTEM_PROMPT
        self._plan_history: list[dict] = []

    async def execute_task(self, task_data: dict) -> Any:
        action = task_data.get("action", "analyze_request")
        if action == "analyze_request":
            return await self._analyze_request(task_data.get("request", ""))
        elif action == "refine_plan":
            return await self._refine_plan(task_data.get("plan"), task_data.get("feedback"))
        elif action == "replan":
            return await self._replan(task_data.get("graph_id"), task_data.get("failed_tasks"))
        return {"error": f"Unknown action: {action}"}

    async def _analyze_request(self, request: str) -> dict:
        """Analyze a user request and produce a plan."""
        prompt = f"""Analyze this user request and produce a structured plan:

Request: {request}

Output a JSON plan with steps assigned to agents. Consider:
- What agents are needed?
- What are the dependencies between steps?
- What is the optimal order?
- What parameters does each step need?"""

        content = await self.think(prompt)

        # Extract JSON plan from response
        plan = self._extract_plan(content, request)
        self._plan_history.append({"request": request, "plan": plan, "timestamp": time.time()})
        await self.observe({"type": "plan_created", "request": request, "steps": len(plan.get("steps", []))})
        return plan

    def _extract_plan(self, llm_output: str, original_request: str) -> dict:
        """Extract or generate a plan from LLM output."""
        import re
        # Try to parse JSON from the output
        json_match = re.search(r'\{[\s\S]*"steps"[\s\S]*\}', llm_output)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: generate a basic plan
        return self._generate_fallback_plan(original_request)

    def _generate_fallback_plan(self, request: str) -> dict:
        """Generate a basic plan when LLM output can't be parsed."""
        request_lower = request.lower()
        steps = []
        step_id = 0

        # Check for web search
        if any(w in request_lower for w in ["search", "find", "look up", "google", "research", "what is", "who is"]):
            steps.append({
                "id": f"s{step_id}", "agent": "research_agent", "action": "web_search",
                "params": {"query": request}, "depends_on": [], "priority": 10,
            })
            step_id += 1
            steps.append({
                "id": f"s{step_id}", "agent": "memory_agent", "action": "store_result",
                "params": {"source": "research"}, "depends_on": ["s0"], "priority": 5,
            })

        # Check for coding
        if any(w in request_lower for w in ["code", "program", "script", "function", "debug", "fix", "write"]):
            steps.append({
                "id": f"s{step_id}", "agent": "coding_agent", "action": "analyze_or_implement",
                "params": {"request": request}, "depends_on": steps[-1:][0]["depends_on"] if steps else [], "priority": 8,
            })

        # Check for file operations
        if any(w in request_lower for w in ["file", "folder", "directory", "list", "read", "save"]):
            steps.append({
                "id": f"s{step_id}", "agent": "executor_agent", "action": "execute_tool",
                "params": {"request": request, "tool_hint": "file_manager"}, "depends_on": [], "priority": 7,
            })

        # Default: use executor
        if not steps:
            steps.append({
                "id": "s0", "agent": "executor_agent", "action": "execute_tool",
                "params": {"request": request}, "depends_on": [], "priority": 5,
            })

        return {
            "steps": steps,
            "reasoning": f"Automatically generated plan for: {request[:100]}",
            "estimated_complexity": "simple" if len(steps) <= 2 else "medium",
        }

    async def _refine_plan(self, plan: dict, feedback: str) -> dict:
        """Refine a plan based on feedback."""
        prompt = f"""Refine this plan based on feedback:

Original Plan: {json.dumps(plan, indent=2)}
Feedback: {feedback}

Output updated JSON plan."""
        content = await self.think(prompt)
        return self._extract_plan(content, str(plan))

    async def _replan(self, graph_id: str, failed_tasks: list) -> dict:
        """Replan around failed tasks."""
        prompt = f"""Create an alternative plan for graph {graph_id}.
Failed tasks: {json.dumps(failed_tasks, indent=2)}
Provide alternative approaches to accomplish the goal."""
        content = await self.think(prompt)
        return self._extract_plan(content, f"Replan for graph {graph_id}")

    def get_plan_history(self) -> list[dict]:
        return self._plan_history[-20:]
