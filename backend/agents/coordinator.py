"""
Coordinator - central task manager for multi-agent system.
Manages task queues, dependency tracking, agent lifecycle, and concurrency.
"""
import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from typing import Optional

from agents.message_bus import MessageBus, Message, MessageType
from agents.task_graph import TaskGraph, Task, TaskStatus
from agents.base_agent import BaseAgent, AgentState
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.critic_agent import CriticAgent
from agents.memory_agent import MemoryAgent
from agents.research_agent import ResearchAgent
from agents.coding_agent import CodingAgent
from agents.automation_agent import AutomationAgent
from mcp.server_manager import MCPServerManager
from mcp.adapters import MCPToolAdapter
from ollama_client import OllamaClient
from memory.memory_manager import MemoryManager
from memory.vector_memory import VectorMemory
from security.permissions import PermissionManager
from skills_engine.skill_manager import SkillManager
from models.router import ModelRouter

logger = logging.getLogger(__name__)


class Coordinator:
    """Central coordinator for the multi-agent system."""

    def __init__(
        self,
        ollama: OllamaClient,
        memory: MemoryManager,
        vector_memory: VectorMemory,
        permissions: PermissionManager,
        skills: SkillManager,
        bus: MessageBus,
        router: ModelRouter,
    ):
        self.ollama = ollama
        self.memory = memory
        self.vector_memory = vector_memory
        self.permissions = permissions
        self.skills = skills
        self.bus = bus
        self.router = router

        # Graphs and queues
        self._active_graphs: dict[str, TaskGraph] = {}
        self._completed_graphs: list[TaskGraph] = []
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._agent_states: dict[str, AgentState] = {}

        # Concurrency control
        self._max_concurrent = 4
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._shutdown_event = asyncio.Event()

        # Agents
        self.agents: dict[str, BaseAgent] = {}
        self._init_agents()

        # Background workers
        self._worker_task = None
        self._monitor_task = None

        # MCP System
        self.mcp_manager = MCPServerManager()
        self.mcp_adapter = MCPToolAdapter()

        # Event log
        self._event_log: list[dict] = []
        self._max_events = 500

    def _init_agents(self):
        """Initialize all specialized agents."""
        agent_classes = {
            "planner_agent": PlannerAgent,
            "executor_agent": ExecutorAgent,
            "critic_agent": CriticAgent,
            "memory_agent": MemoryAgent,
            "research_agent": ResearchAgent,
            "coding_agent": CodingAgent,
            "automation_agent": AutomationAgent,
        }
        for name, cls in agent_classes.items():
            try:
                agent = cls(
                    name=name,
                    ollama=self.ollama,
                    memory=self.memory,
                    permissions=self.permissions,
                    skills=self.skills,
                    message_bus=self.bus,
                    model_router=self.router,
                )
                self.agents[name] = agent
                self._agent_states[name] = AgentState.IDLE
                logger.info(f"Initialized agent: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize agent {name}: {e}")

        # Subscribe coordinator to bus
        self.bus.subscribe("coordinator", self._on_message)

    async def _on_message(self, message: Message):
        """Handle coordinator-level messages."""
        if message.type == MessageType.TASK_RESULT:
            self._log_event("task_result", {"agent": message.sender, "task_id": message.payload.get("task_id")})
        elif message.type == MessageType.ERROR:
            self._log_event("agent_error", {"agent": message.sender, "error": message.payload.get("error")})
        elif message.type == MessageType.AGENT_STATUS:
            if message.sender in self._agent_states:
                self._agent_states[message.sender] = AgentState(message.payload.get("state", "idle"))

    async def start(self):
        """Start the coordinator's background workers."""
        self._worker_task = asyncio.create_task(self._queue_worker())
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        await self.mcp_manager.start()
        logger.info("Coordinator started with MCP support")

    async def stop(self):
        """Gracefully stop all agent activities."""
        self._shutdown_event.set()
        for task in self._running_tasks.values():
            task.cancel()
        if self._worker_task:
            self._worker_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()
        for agent in self.agents.values():
            await agent.cleanup()
        await self.mcp_manager.stop()
        logger.info("Coordinator stopped")

    async def submit_request(self, request: str, user_id: str = "user") -> dict:
        """Submit a user request to the multi-agent system."""
        graph_id = str(uuid.uuid4())
        graph = TaskGraph(graph_id)
        graph.metadata = {"request": request, "user_id": user_id}

        # Step 1: Planner analyzes the request
        plan_task = Task(
            task_id=f"{graph_id}_plan",
            agent="planner_agent",
            action="analyze_request",
            params={"request": request},
            priority=10,
        )
        graph.add_task(plan_task)
        self._active_graphs[graph_id] = graph

        # Send request to planner
        msg = Message(
            msg_type=MessageType.TASK_ASSIGN,
            sender="coordinator",
            recipient="planner_agent",
            payload={"task_id": plan_task.id, "request": request, "graph_id": graph_id},
            correlation_id=plan_task.id,
        )
        await self.bus.publish(msg)
        plan_task.status = TaskStatus.RUNNING
        self._log_event("request_submitted", {"graph_id": graph_id, "request": request[:100]})

        return {"graph_id": graph_id, "status": "submitted", "plan_task_id": plan_task.id}

    async def _queue_worker(self):
        """Background worker that processes the task queue."""
        while not self._shutdown_event.is_set():
            try:
                priority, task_id, graph_id, agent_name, action, params = await asyncio.wait_for(
                    self._task_queue.get(), timeout=2.0
                )
                async with self._semaphore:
                    task = asyncio.create_task(
                        self._execute_queued_task(graph_id, task_id, agent_name, action, params)
                    )
                    self._running_tasks[task_id] = task
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Queue worker error: {e}")

    async def _execute_queued_task(self, graph_id: str, task_id: str, agent_name: str, action: str, params: dict):
        """Execute a queued task."""
        graph = self._active_graphs.get(graph_id)
        if not graph:
            return

        agent = self.agents.get(agent_name)
        if not agent:
            graph.mark_failed(task_id, f"Agent {agent_name} not found")
            return

        task = graph.tasks.get(task_id)
        if not task:
            return

        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._agent_states[agent_name] = AgentState.EXECUTING
        self._log_event("task_started", {"graph_id": graph_id, "task_id": task_id, "agent": agent_name})

        try:
            result = await agent.execute_task({"action": action, **params})
            graph.mark_completed(task_id, result)
            self._agent_states[agent_name] = AgentState.IDLE
            self._log_event("task_completed", {"graph_id": graph_id, "task_id": task_id, "agent": agent_name})

            # Check for next ready tasks
            ready = graph.get_ready_tasks()
            for next_task in ready:
                await self._enqueue_task(graph_id, next_task)

            # Check graph completion
            if not graph.has_unfinished_tasks():
                self._finalize_graph(graph_id)

        except Exception as e:
            graph.mark_failed(task_id, str(e))
            self._agent_states[agent_name] = AgentState.FAILED
            self._log_event("task_failed", {"graph_id": graph_id, "task_id": task_id, "agent": agent_name, "error": str(e)})

        finally:
            self._running_tasks.pop(task_id, None)

    async def _enqueue_task(self, graph_id: str, task: Task):
        """Enqueue a task for execution."""
        priority = -task.priority  # Negative for highest-first ordering
        await self._task_queue.put((priority, task.id, graph_id, task.agent, task.action, task.params))
        self._log_event("task_queued", {"graph_id": graph_id, "task_id": task.id, "agent": task.agent})

    def _finalize_graph(self, graph_id: str):
        """Move graph to completed state and record summary."""
        graph = self._active_graphs.pop(graph_id, None)
        if graph:
            self._completed_graphs.append(graph)
            if len(self._completed_graphs) > 50:
                self._completed_graphs = self._completed_graphs[-50:]
            self._log_event("graph_completed", {
                "graph_id": graph_id,
                "status": graph.status.value,
                "total_tasks": graph.get_task_count(),
                "completed": graph.get_task_count(TaskStatus.COMPLETED),
                "failed": graph.get_task_count(TaskStatus.FAILED),
            })

    def _log_event(self, event_type: str, data: dict):
        """Log a coordinator event."""
        entry = {"type": event_type, "data": data, "timestamp": time.time()}
        self._event_log.append(entry)
        if len(self._event_log) > self._max_events:
            self._event_log = self._event_log[-self._max_events:]
        logger.debug(f"Coordinator event: {event_type} - {data}")

    def get_graph(self, graph_id: str) -> Optional[dict]:
        graph = self._active_graphs.get(graph_id)
        if not graph:
            graph = next((g for g in self._completed_graphs if g.id == graph_id), None)
        return graph.to_dict() if graph else None

    def get_all_graphs(self, limit: int = 20) -> list[dict]:
        graphs = list(self._active_graphs.values()) + self._completed_graphs
        return [g.to_dict() for g in graphs[-limit:]]

    def cancel_graph(self, graph_id: str) -> bool:
        graph = self._active_graphs.get(graph_id)
        if graph:
            graph.cancel()
            self._log_event("graph_cancelled", {"graph_id": graph_id})
            return True
        return False

    def cancel_task(self, graph_id: str, task_id: str) -> bool:
        graph = self._active_graphs.get(graph_id)
        if graph:
            graph.cancel(task_id)
            run_task = self._running_tasks.pop(task_id, None)
            if run_task:
                run_task.cancel()
            return True
        return False

    async def _monitor_loop(self):
        """Periodic monitoring of agent states."""
        while not self._shutdown_event.is_set():
            await asyncio.sleep(5)
            for name, agent in self.agents.items():
                status = agent.get_status()
                self._agent_states[name] = AgentState(status.get("state", "idle"))

    def get_agent_statuses(self) -> dict[str, dict]:
        statuses = {}
        for name, agent in self.agents.items():
            try:
                statuses[name] = agent.get_status()
            except Exception as e:
                statuses[name] = {"name": name, "state": "unknown", "error": str(e)}
        return statuses

    def get_event_log(self, limit: int = 100) -> list[dict]:
        return self._event_log[-limit:]

    def get_status_summary(self) -> dict:
        return {
            "active_graphs": len(self._active_graphs),
            "completed_graphs": len(self._completed_graphs),
            "running_tasks": len(self._running_tasks),
            "queue_size": self._task_queue.qsize(),
            "agents": self.get_agent_statuses(),
            "agent_states": {k: v.value for k, v in self._agent_states.items()},
            "event_count": len(self._event_log),
            "mcp_servers": len(self.mcp_manager.get_all_servers()),
        }
