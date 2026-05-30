import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, List, Optional
from dataclasses import dataclass, field
from uuid import uuid4

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class WorkflowStep:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    action: str = ""
    params: dict = field(default_factory=dict)
    permission_level: str = "safe"
    depends_on: list = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    error: str = ""


@dataclass
class WorkflowTrigger:
    type: str = "manual"
    event_type: str = ""
    cron_expr: str = ""
    condition: str = ""


@dataclass
class Workflow:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    trigger: WorkflowTrigger = field(default_factory=WorkflowTrigger)
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.IDLE
    created_at: float = field(default_factory=time.time)
    last_run: float = 0.0
    run_count: int = 0
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger": {
                "type": self.trigger.type,
                "event_type": self.trigger.event_type,
                "cron_expr": self.trigger.cron_expr,
                "condition": self.trigger.condition,
            },
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "action": s.action,
                    "params": s.params,
                    "permission_level": s.permission_level,
                    "depends_on": s.depends_on,
                    "status": s.status,
                }
                for s in self.steps
            ],
            "status": self.status.value,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "enabled": self.enabled,
        }


class WorkflowEngine:
    def __init__(self):
        self._workflows: dict = {}
        self._running: dict = {}
        self._action_handlers: dict = {}
        self._approval_callback: Optional[Callable] = None

    def set_approval_callback(self, callback: Callable):
        self._approval_callback = callback

    def register_action(self, action_type: str, handler: Callable):
        self._action_handlers[action_type] = handler

    def add_workflow(self, workflow: Workflow) -> str:
        self._workflows[workflow.id] = workflow
        logger.info(f"Added workflow: {workflow.name} ({workflow.id[:8]}...)")
        return workflow.id

    def remove_workflow(self, workflow_id: str) -> bool:
        return self._workflows.pop(workflow_id, None) is not None

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        wf = self._workflows.get(workflow_id)
        return wf.to_dict() if wf else None

    def get_workflows(self) -> list:
        return [wf.to_dict() for wf in self._workflows.values()]

    async def run_workflow(self, workflow_id: str) -> dict:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return {"error": "Workflow not found"}
        if wf.status == WorkflowStatus.RUNNING:
            return {"error": "Workflow already running"}
        wf.status = WorkflowStatus.RUNNING
        wf.last_run = time.time()
        wf.run_count += 1
        asyncio.create_task(self._execute_workflow(wf))
        return {"status": "started", "workflow_id": workflow_id}

    async def _execute_workflow(self, wf: Workflow):
        try:
            completed = set()
            while True:
                pending = [s for s in wf.steps if s.status == "pending" and all(d in completed for d in s.depends_on)]
                if not pending:
                    break
                for step in pending:
                    step.status = "running"
                    result = await self._execute_step(wf, step)
                    if result.get("error"):
                        step.status = "failed"
                        step.error = result["error"]
                        wf.status = WorkflowStatus.FAILED
                        logger.error(f"Workflow '{wf.name}' step '{step.name}' failed: {result['error']}")
                        return
                    step.status = "completed"
                    step.result = result
                    completed.add(step.id)
            wf.status = WorkflowStatus.COMPLETED
            logger.info(f"Workflow '{wf.name}' completed successfully")
        except Exception as e:
            wf.status = WorkflowStatus.FAILED
            logger.error(f"Workflow '{wf.name}' failed: {e}")

    async def _execute_step(self, wf: Workflow, step: WorkflowStep) -> dict:
        handler = self._action_handlers.get(step.action)
        if not handler:
            return {"error": f"No handler for action '{step.action}'"}
        if step.permission_level in ("high", "critical") and self._approval_callback:
            wf.status = WorkflowStatus.AWAITING_APPROVAL
            approved = await self._approval_callback(wf.id, step)
            if not approved:
                return {"error": "Step rejected by user"}
            wf.status = WorkflowStatus.RUNNING
        try:
            result = handler(**step.params)
            if asyncio.iscoroutine(result):
                result = await result
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}

    def cancel_workflow(self, workflow_id: str) -> bool:
        wf = self._workflows.get(workflow_id)
        if wf and wf.status == WorkflowStatus.RUNNING:
            wf.status = WorkflowStatus.CANCELLED
            return True
        return False

    def handle_event(self, event_type: str, payload: dict = None):
        for wf in self._workflows.values():
            if wf.enabled and wf.trigger.type == "event" and wf.trigger.event_type == event_type:
                if wf.status != WorkflowStatus.RUNNING:
                    asyncio.create_task(self.run_workflow(wf.id))
