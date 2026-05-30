"""
Automation Agent - manages recurring workflows, scheduled tasks, and event-driven automation.
Cannot execute HIGH/CRITICAL actions autonomously.
"""
import asyncio
import json
import logging
import time
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

AUTOMATION_SYSTEM_PROMPT = """You are JARVIS Automation Agent. Your role is to:
1. Create and manage recurring workflows
2. Schedule tasks for future execution
3. Handle event-driven automation triggers
4. Monitor workflow health and report issues

IMPORTANT SAFETY RULE: You cannot execute HIGH or CRITICAL risk actions autonomously.
Any such actions must be flagged for user approval first."""


class AutomationAgent(BaseAgent):
    """Manages scheduled tasks and recurring workflows."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.system_prompt = AUTOMATION_SYSTEM_PROMPT
        self._scheduled_tasks: dict[str, dict] = {}
        self._workflows: dict[str, dict] = {}
        self._scheduler_task = None
        self._running = False

    async def start_scheduler(self):
        """Start the background scheduler."""
        if not self._running:
            self._running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop_scheduler(self):
        """Stop the background scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()

    async def execute_task(self, task_data: dict) -> Any:
        action = task_data.get("action", "list_scheduled")
        handlers = {
            "list_scheduled": self._list_scheduled,
            "schedule_task": self._schedule_task,
            "cancel_scheduled": self._cancel_scheduled,
            "create_workflow": self._create_workflow,
            "run_workflow": self._run_workflow,
            "list_workflows": self._list_workflows,
            "check_health": self._check_health,
        }
        handler = handlers.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        return await handler(task_data)

    async def _schedule_task(self, task_data: dict) -> dict:
        """Schedule a task for future execution."""
        name = task_data.get("name", f"task_{int(time.time())}")
        delay = task_data.get("delay_seconds", 60)
        action = task_data.get("action_type", "executor_agent")
        params = task_data.get("params", {})
        recurring = task_data.get("recurring", False)
        interval = task_data.get("interval_seconds", 0)

        # Safety check for HIGH/CRITICAL actions
        risk_level = self._assess_risk(action, params)
        if risk_level in ("high", "critical"):
            return {
                "status": "rejected",
                "reason": "Automation agent cannot schedule HIGH or CRITICAL actions autonomously",
                "suggested_action": "Request user approval before scheduling this task",
            }

        task_id = f"sch_{int(time.time())}_{name}"
        self._scheduled_tasks[task_id] = {
            "id": task_id,
            "name": name,
            "action": action,
            "params": params,
            "delay": delay,
            "recurring": recurring,
            "interval": interval,
            "created_at": time.time(),
            "next_run": time.time() + delay,
            "run_count": 0,
            "status": "scheduled",
        }

        await self.observe({"type": "task_scheduled", "name": name, "delay": delay})
        return {"status": "scheduled", "task_id": task_id, "next_run": self._scheduled_tasks[task_id]["next_run"]}

    def _assess_risk(self, action: str, params: dict) -> str:
        """Assess the risk level of an action."""
        high_keywords = ["delete", "remove", "format", "shutdown", "install", "shell", "powershell", "system"]
        for keyword in high_keywords:
            if keyword in action.lower() or keyword in str(params).lower():
                return "high"
        return "low"

    async def _cancel_scheduled(self, task_data: dict) -> dict:
        """Cancel a scheduled task."""
        task_id = task_data.get("task_id", "")
        if task_id in self._scheduled_tasks:
            self._scheduled_tasks[task_id]["status"] = "cancelled"
            return {"status": "cancelled", "task_id": task_id}
        return {"error": f"Task not found: {task_id}"}

    async def _list_scheduled(self, task_data: dict = None) -> dict:
        """List all scheduled tasks."""
        active = {k: v for k, v in self._scheduled_tasks.items() if v.get("status") == "scheduled"}
        return {"scheduled_tasks": list(active.values())}

    async def _create_workflow(self, task_data: dict) -> dict:
        """Create a reusable workflow definition."""
        name = task_data.get("name", f"workflow_{int(time.time())}")
        steps = task_data.get("steps", [])
        trigger = task_data.get("trigger", "manual")  # manual, scheduled, event

        # Validate steps for safety
        for step in steps:
            risk = self._assess_risk(step.get("action", ""), step.get("params", {}))
            if risk in ("high", "critical"):
                step["requires_approval"] = True
                step["approved"] = False

        workflow_id = f"wf_{int(time.time())}"
        self._workflows[workflow_id] = {
            "id": workflow_id,
            "name": name,
            "steps": steps,
            "trigger": trigger,
            "created_at": time.time(),
            "run_count": 0,
            "status": "active",
        }

        await self.observe({"type": "workflow_created", "name": name, "steps": len(steps)})
        return {"status": "created", "workflow_id": workflow_id, "steps_count": len(steps)}

    async def _run_workflow(self, task_data: dict) -> dict:
        """Run a workflow immediately."""
        workflow_id = task_data.get("workflow_id", "")
        workflow = self._workflows.get(workflow_id)

        if not workflow:
            return {"error": f"Workflow not found: {workflow_id}"}

        if workflow["status"] != "active":
            return {"error": "Workflow is not active"}

        # Execute each step sequentially
        results = []
        for i, step in enumerate(workflow["steps"]):
            if step.get("requires_approval") and not step.get("approved"):
                results.append({"step": i, "status": "requires_approval", "action": step.get("action")})
                continue

            try:
                # Execute via appropriate agent
                agent = step.get("agent", "executor_agent")
                result = await self._execute_step(agent, step)
                results.append({"step": i, "status": "completed", "result": result})
            except Exception as e:
                results.append({"step": i, "status": "failed", "error": str(e)})
                break

        workflow["run_count"] += 1
        return {"workflow_id": workflow_id, "results": results, "completed": all(r["status"] == "completed" for r in results)}

    async def _execute_step(self, agent: str, step: dict) -> Any:
        """Execute a single workflow step."""
        action = step.get("action", "")
        params = step.get("params", {})

        # Route to the appropriate agent
        from agents.message_bus import Message, MessageType
        msg = Message(
            msg_type=MessageType.TASK_ASSIGN,
            sender=self.name,
            recipient=agent,
            payload={"action": action, **params},
        )
        response = await self.bus.request(msg, timeout=60.0)
        if response:
            return response.payload
        return {"error": "No response from agent"}

    async def _list_workflows(self, task_data: dict = None) -> dict:
        """List all defined workflows."""
        return {"workflows": list(self._workflows.values())}

    async def _check_health(self, task_data: dict = None) -> dict:
        """Check health of scheduled tasks."""
        now = time.time()
        overdue = [
            {"id": tid, "name": t["name"], "scheduled": t["next_run"]}
            for tid, t in self._scheduled_tasks.items()
            if t["status"] == "scheduled" and t["next_run"] < now - 300
        ]
        return {
            "scheduled_count": sum(1 for t in self._scheduled_tasks.values() if t["status"] == "scheduled"),
            "overdue_count": len(overdue),
            "overdue": overdue[:5],
            "workflow_count": len(self._workflows),
            "scheduler_running": self._running,
        }

    async def _scheduler_loop(self):
        """Background loop that triggers scheduled tasks."""
        while self._running:
            now = time.time()
            for task_id, task in list(self._scheduled_tasks.items()):
                if task["status"] != "scheduled":
                    continue
                if now >= task["next_run"]:
                    try:
                        # Execute the scheduled task
                        msg = Message(
                            msg_type=MessageType.TASK_ASSIGN,
                            sender=self.name,
                            recipient=task["action"],
                            payload=task["params"],
                        )
                        await self.bus.publish(msg)
                        task["run_count"] += 1

                        if task["recurring"] and task["interval"] > 0:
                            task["next_run"] = now + task["interval"]
                        else:
                            task["status"] = "completed"

                        await self.observe({"type": "scheduled_task_executed", "task_id": task_id, "name": task["name"]})
                    except Exception as e:
                        logger.error(f"Scheduled task {task_id} failed: {e}")
                        task["status"] = "failed"
                        task["error"] = str(e)

            await asyncio.sleep(10)  # Check every 10 seconds

    async def cleanup(self):
        await self.stop_scheduler()
        await super().cleanup()
