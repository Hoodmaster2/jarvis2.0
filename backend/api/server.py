"""
FastAPI server with all API routes for JARVIS.
"""
import json
import logging
import os
import platform
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from config import Config
from ollama_client import OllamaClient
from memory.memory_manager import MemoryManager
from memory.vector_memory import VectorMemory
from security.permissions import PermissionManager
from skills_engine.skill_manager import SkillManager
from agents.orchestrator import Orchestrator
from agents.message_bus import MessageBus
from agents.task_graph import TaskGraph, Task, TaskStatus
from agents.coordinator import Coordinator
from agents.background_agent import BackgroundAgent
from models.router import ModelRouter
from tools.registry import get_registry, ToolRegistry
from tools.schemas import ToolSchema, ToolAction, ToolParameter, PermissionLevel as ToolPermissionLevel
from background.daemon import BackgroundDaemon
from background.event_bus import BackgroundEventBus, Event, EventPriority
from background.scheduler import Scheduler, ScheduledTask
from background.task_queue import TaskQueue, QueueTask
from background.observers import ObserverRegistry, Observer
from background.notifications import NotificationManager, Notification, NotificationLevel
from workflows.workflow_engine import WorkflowEngine, Workflow, WorkflowStep, WorkflowTrigger
from mcp.server_manager import MCPServerManager
from mcp.schemas import MCPServerConfig
from mcp.discovery import COMMON_MCP_SERVERS
from coding.repo_indexer import RepoIndexer
from coding.semantic_search import SemanticSearch
from coding.git_manager import GitManager
from coding.patch_engine import PatchEngine
from coding.dependency_analyzer import DependencyAnalyzer
from coding.workspace_manager import WorkspaceManager
from coding.code_memory import CodeMemory
from coding.ast_parser import ASTParser
from vision.screen_capture import ScreenCapture
from vision.ocr_engine import OCREngine
from vision.image_analyzer import ImageAnalyzer
from vision.ui_detector import UIDetector
from vision.desktop_context import DesktopContext
from vision.visual_memory import VisualMemory
from vision.window_tracker import WindowTracker
from browser_worker.browser_manager import BrowserManager
from browser_worker.browser_task_memory import BrowserTaskMemory
from browser_worker.dom_actions import (
    click_element, fill_form, get_text_content, get_page_info,
    get_visible_text, get_links, get_forms, get_html,
    check_element, fill_form_fields,
)
from browser_worker.page_utils import (
    take_screenshot, summarize_page, safe_scrape, test_links,
    seo_audit, check_uptime, monitor_page_changes,
)
from browser_worker.form_filler import (
    classify_form, fill_form_safe, submit_form_safe,
)
from memory.hybrid_memory import HybridMemory
from learning.failure_analyzer import FailureAnalyzer
from learning.workflow_learner import WorkflowLearner
from learning.prompt_optimizer import PromptOptimizer
from learning.recommendation_engine import RecommendationEngine
from learning.correction_tracker import CorrectionTracker
from desktop.mouse_controller import MouseController
from desktop.keyboard_controller import KeyboardController
from desktop.window_manager import WindowManager
from desktop.ui_automation import UIAutomation
from desktop.clipboard_manager import ClipboardManager
from desktop.app_state_detector import AppStateDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jarvis")

# Global state
config: Config = None
ollama: OllamaClient = None
memory: MemoryManager = None
vector_memory: VectorMemory = None
permissions: PermissionManager = None
skills: SkillManager = None
orchestrator: Orchestrator = None
message_bus: MessageBus = None
model_router: ModelRouter = None
coordinator: Coordinator = None
background_daemon: BackgroundDaemon = None
background_agent: BackgroundAgent = None
workflow_engine: WorkflowEngine = None
tool_registry: ToolRegistry = None
mcp_manager: MCPServerManager = None
repo_indexer: RepoIndexer = None
semantic_search: SemanticSearch = None
git_manager: GitManager = None
patch_engine: PatchEngine = None
dep_analyzer: DependencyAnalyzer = None
workspace_manager: WorkspaceManager = None
code_memory: CodeMemory = None
ast_parser: ASTParser = None
screen_capture: ScreenCapture = None
ocr_engine: OCREngine = None
image_analyzer: ImageAnalyzer = None
ui_detector: UIDetector = None
desktop_context: DesktopContext = None
visual_memory: VisualMemory = None
window_tracker: WindowTracker = None
# Phase 8: Browser Worker
browser_manager: BrowserManager = None
browser_task_memory: BrowserTaskMemory = None
# Phase 9: Hybrid Memory
hybrid_memory: HybridMemory = None
# Phase 10: Learning
failure_analyzer: FailureAnalyzer = None
workflow_learner: WorkflowLearner = None
prompt_optimizer: PromptOptimizer = None
recommendation_engine: RecommendationEngine = None
correction_tracker: CorrectionTracker = None
# Phase 12: Desktop
mouse_controller: MouseController = None
keyboard_controller: KeyboardController = None
window_manager: WindowManager = None
ui_automation: UIAutomation = None
clipboard_manager: ClipboardManager = None
app_state_detector: AppStateDetector = None


# --- Pydantic Models ---

class ChatRequest(BaseModel):
    message: str
    history: list = []
    stream: bool = True


class MemorySearchRequest(BaseModel):
    query: str
    type: Optional[str] = None
    limit: int = 20


class MemoryCreateRequest(BaseModel):
    type: str
    content: str
    metadata: dict = {}


class SkillToggleRequest(BaseModel):
    name: str
    enabled: bool


class PermissionActionRequest(BaseModel):
    action_id: str
    approved: bool


class ExecuteSkillRequest(BaseModel):
    skill_name: str
    command: str
    args: dict = {}


class SettingsUpdateRequest(BaseModel):
    key: str
    value: str


class ShellCommandRequest(BaseModel):
    command: str
    description: str = ""


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    global config, ollama, memory, vector_memory, permissions, skills, orchestrator, message_bus, model_router, coordinator, background_daemon, background_agent, workflow_engine, tool_registry
    global mcp_manager, repo_indexer, semantic_search, git_manager, patch_engine, dep_analyzer, workspace_manager, code_memory, ast_parser
    global screen_capture, ocr_engine, image_analyzer, ui_detector, desktop_context, visual_memory, window_tracker
    global browser_manager, browser_task_memory, hybrid_memory
    global failure_analyzer, workflow_learner, prompt_optimizer, recommendation_engine, correction_tracker
    global mouse_controller, keyboard_controller, window_manager, ui_automation, clipboard_manager, app_state_detector
    config = Config()
    ollama = OllamaClient(config.ollama_host, config.ollama_model)
    memory = MemoryManager(config.memory_path)

    async def _embed(text: str):
        try:
            return await ollama.embed(text)
        except Exception:
            return []

    vector_memory = VectorMemory(
        embed_fn=lambda text: __import__('asyncio').run(_embed(text)),
        backend=os.getenv("VECTOR_BACKEND", "memory"),
        persist_dir=str(Path(config.get("memory", "path", default="./data/memory.db")).parent / "vectors"),
    )
    permissions = PermissionManager()
    skills = SkillManager()
    tool_registry = get_registry()
    background_daemon = BackgroundDaemon()
    workflow_engine = WorkflowEngine()
    orchestrator = Orchestrator(ollama, memory, permissions, skills, tool_registry=tool_registry)
    message_bus = MessageBus()
    model_router = ModelRouter(ollama, config.ollama_model)
    coordinator = Coordinator(ollama, memory, vector_memory, permissions, skills, message_bus, model_router)
    mcp_manager = coordinator.mcp_manager
    background_agent = BackgroundAgent(ollama, memory, vector_memory, permissions, skills, background_daemon)
    # Phase 6: Coding system
    repo_indexer = RepoIndexer()
    semantic_search = SemanticSearch()
    git_manager = GitManager()
    patch_engine = PatchEngine()
    dep_analyzer = DependencyAnalyzer()
    workspace_manager = WorkspaceManager()
    code_memory = CodeMemory()
    ast_parser = ASTParser()
    # Phase 7: Vision system
    screen_capture = ScreenCapture()
    ocr_engine = OCREngine()
    image_analyzer = ImageAnalyzer()
    ui_detector = UIDetector()
    desktop_context = DesktopContext(screen_capture, ocr_engine)
    visual_memory = VisualMemory()
    window_tracker = WindowTracker()
    # Phase 8: Browser Worker
    browser_manager = BrowserManager()
    browser_task_memory = BrowserTaskMemory()
    # Phase 9: Hybrid Memory
    hybrid_memory = HybridMemory(embed_fn=lambda text: __import__('asyncio').run(_embed(text)))
    # Phase 10: Learning
    failure_analyzer = FailureAnalyzer()
    workflow_learner = WorkflowLearner()
    prompt_optimizer = PromptOptimizer()
    recommendation_engine = RecommendationEngine()
    correction_tracker = CorrectionTracker()
    # Phase 12: Desktop
    mouse_controller = MouseController()
    keyboard_controller = KeyboardController()
    window_manager = WindowManager()
    clipboard_manager = ClipboardManager()
    app_state_detector = AppStateDetector(window_manager)
    ui_automation = UIAutomation(mouse_controller, keyboard_controller, window_manager)
    await coordinator.start()
    await background_daemon.start()
    await background_agent.start()
    await model_router.refresh()
    logger.info("JARVIS backend started with Phases 8-12 systems")
    yield
    await browser_manager.close_all()
    await background_agent.stop()
    await background_daemon.stop()
    await coordinator.stop()
    if ollama:
        await ollama.close()
    if memory:
        memory.close()
    if hybrid_memory:
        hybrid_memory.close()
    logger.info("JARVIS backend stopped")


def create_app(config_path: str = None):
    global config
    if config_path:
        config = Config(config_path)

    app = FastAPI(title="JARVIS API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_routes(app)
    return app


def _register_routes(app: FastAPI):

    # --- Health & Status ---

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "name": "JARVIS"}

    @app.get("/api/status")
    async def status():
        connected = await ollama.check_connection()
        return {
            "ollama_connected": connected,
            "model": ollama.model,
            "memory_enabled": memory is not None,
            "skills_count": len(skills.get_all_skills()),
            "pending_approvals": permissions.get_pending(),
            "platform": platform.system(),
            "version": "1.0.0",
        }

    # --- Ollama ---

    @app.get("/api/models")
    async def list_models():
        models = await ollama.list_models()
        return {"models": models}

    @app.post("/api/models/set")
    async def set_model(req: dict):
        model = req.get("model")
        if model:
            ollama.model = model
            config.set("ollama", "model", value=model)
            return {"status": "ok", "model": model}
        raise HTTPException(400, "model required")

    # --- Chat ---

    @app.post("/api/chat")
    async def chat(req: ChatRequest):
        async def generate():
            async for chunk in orchestrator.chat(req.message, req.history):
                yield json.dumps(chunk) + "\n"
        return StreamingResponse(generate(), media_type="application/x-ndjson")

    # --- Memory ---

    @app.get("/api/memory")
    async def get_memories(type: str = None, limit: int = 50):
        if type:
            return {"memories": memory.get_memories_by_type(type, limit)}
        return {"memories": memory.get_all_memories(limit)}

    @app.post("/api/memory")
    async def create_memory(req: MemoryCreateRequest):
        mid = memory.add_memory(req.type, req.content, req.metadata)
        return {"id": mid, "status": "created"}

    @app.post("/api/memory/search")
    async def search_memory(req: MemorySearchRequest):
        results = memory.search_memories(req.query, req.type, req.limit)
        return {"results": results}

    @app.delete("/api/memory/{mem_id}")
    async def delete_memory(mem_id: str):
        ok = memory.delete_memory(mem_id)
        if not ok:
            raise HTTPException(404, "Memory not found")
        return {"status": "deleted"}

    @app.delete("/api/memory")
    async def clear_memories():
        memory.clear_all_memories()
        return {"status": "cleared"}

    @app.get("/api/memory/export")
    async def export_memories():
        export_path = "./data/memory_export.json"
        memory.export_memories(export_path)
        return {"status": "exported", "path": export_path}

    @app.get("/api/preferences")
    async def get_preferences():
        return {"preferences": memory.get_all_preferences()}

    @app.post("/api/preferences")
    async def set_preference(req: SettingsUpdateRequest):
        memory.set_preference(req.key, req.value)
        return {"status": "saved"}

    # --- Skills ---

    @app.get("/api/skills")
    async def list_skills():
        return {"skills": skills.get_all_skills()}

    @app.post("/api/skills/toggle")
    async def toggle_skill(req: SkillToggleRequest):
        if req.enabled:
            ok = skills.enable_skill(req.name)
        else:
            ok = skills.disable_skill(req.name)
        return {"status": "ok" if ok else "not_found"}

    @app.post("/api/skills/install")
    async def install_skill(req: dict):
        source = req.get("source")
        if not source:
            raise HTTPException(400, "source required")
        ok = skills.install_skill(source)
        return {"status": "installed" if ok else "failed"}

    @app.post("/api/skills/uninstall")
    async def uninstall_skill(req: dict):
        name = req.get("name")
        if not name:
            raise HTTPException(400, "name required")
        ok = skills.uninstall_skill(name)
        return {"status": "uninstalled" if ok else "not_found"}

    @app.post("/api/skills/reload")
    async def reload_skills():
        skills.reload()
        return {"status": "reloaded"}

    @app.post("/api/skills/execute")
    async def execute_skill(req: ExecuteSkillRequest):
        result = await skills.execute_command(req.skill_name, req.command, **req.args)
        return {"result": result}

    # --- Permissions ---

    @app.get("/api/permissions/pending")
    async def get_pending():
        return {"pending": permissions.get_pending()}

    @app.post("/api/permissions/respond")
    async def respond_permission(req: PermissionActionRequest):
        if req.approved:
            ok = permissions.approve(req.action_id)
        else:
            ok = permissions.deny(req.action_id)
        if not ok:
            raise HTTPException(404, "Action not found")
        return {"status": "processed", "approved": req.approved}

    @app.get("/api/permissions/describe")
    async def describe_action(action: str, details: str = ""):
        return permissions.describe_action(action, details)

    # --- Systems ---

    @app.get("/api/system/info")
    async def system_info():
        import psutil
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "memory": dict(psutil.virtual_memory()._asdict()),
                "disk": dict(psutil.disk_usage("/")._asdict()),
                "platform": platform.system(),
                "platform_version": platform.version(),
                "hostname": platform.node(),
            }
        except ImportError:
            return {"error": "psutil not installed"}

    # --- Config ---

    @app.get("/api/config")
    async def get_config():
        return config.to_dict()

    @app.post("/api/config")
    async def update_config(req: SettingsUpdateRequest):
        parts = req.key.split(".")
        if len(parts) >= 2:
            config.set(*parts, value=req.value)
            return {"status": "saved"}
        raise HTTPException(400, "Use dot notation: section.key")

    # --- File operations (proxy to skills) ---

    @app.post("/api/shell")
    async def run_shell(req: ShellCommandRequest):
        """Run a PowerShell command with permission check."""
        import asyncio
        import subprocess

        desc = permissions.describe_action("shell", req.command)
        if desc["needs_confirmation"]:
            # In a real scenario, this would wait for user approval
            # For now, we surface the need for approval
            return {
                "status": "needs_approval",
                "action_id": str(uuid.uuid4()),
                "description": f"Run PowerShell command: {req.command}",
                "level": desc["level"],
            }

        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-Command", req.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return {
                "status": "done",
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # --- Conversations ---

    @app.get("/api/conversations/{session_id}")
    async def get_conversation(session_id: str):
        return {"conversation": memory.get_conversation_history(session_id)}

    # ============================================================
    # Multi-Agent System Endpoints
    # ============================================================

    # --- Agent Status ---

    @app.get("/api/agents")
    async def list_agents():
        """Get status of all agents in the multi-agent system."""
        return {"agents": coordinator.get_agent_statuses()}

    @app.get("/api/agents/{agent_name}")
    async def get_agent(agent_name: str):
        """Get detailed status of a specific agent."""
        statuses = coordinator.get_agent_statuses()
        agent = statuses.get(agent_name)
        if not agent:
            raise HTTPException(404, f"Agent '{agent_name}' not found")
        return {"agent": agent}

    @app.post("/api/agents/{agent_name}/assign-model")
    async def assign_agent_model(agent_name: str, req: dict):
        """Assign a specific model to an agent."""
        model = req.get("model")
        if not model:
            raise HTTPException(400, "model required")
        model_router.assign_model(agent_name, model)
        return {"status": "assigned", "agent": agent_name, "model": model}

    # --- Task Graphs ---

    @app.post("/api/graphs/submit")
    async def submit_request(req: dict):
        """Submit a request to the multi-agent system."""
        request_text = req.get("request", "")
        if not request_text:
            raise HTTPException(400, "request required")
        result = await coordinator.submit_request(request_text, user_id=req.get("user_id", "user"))
        return result

    @app.get("/api/graphs")
    async def list_graphs(limit: int = 20):
        """List all task graphs (active and completed)."""
        return {"graphs": coordinator.get_all_graphs(limit)}

    @app.get("/api/graphs/{graph_id}")
    async def get_graph(graph_id: str):
        """Get details of a specific task graph."""
        graph = coordinator.get_graph(graph_id)
        if not graph:
            raise HTTPException(404, f"Graph '{graph_id}' not found")
        return {"graph": graph}

    @app.get("/api/graphs/{graph_id}/dag")
    async def get_graph_dag(graph_id: str):
        """Get DAG visualization data for a graph."""
        graph = coordinator.get_graph(graph_id)
        if not graph:
            raise HTTPException(404, f"Graph '{graph_id}' not found")
        # Reconstruct DAG from tasks
        nodes = []
        edges = []
        for task in graph.get("tasks", []):
            nodes.append({
                "id": task["id"],
                "label": task["action"],
                "agent": task["agent"],
                "status": task["status"],
            })
            for dep in task.get("depends_on", []):
                edges.append({"from": dep, "to": task["id"]})
        return {"nodes": nodes, "edges": edges}

    @app.post("/api/graphs/{graph_id}/cancel")
    async def cancel_graph(graph_id: str):
        """Cancel a task graph."""
        ok = coordinator.cancel_graph(graph_id)
        return {"status": "cancelled" if ok else "not_found"}

    @app.post("/api/graphs/{graph_id}/tasks/{task_id}/cancel")
    async def cancel_task(graph_id: str, task_id: str):
        """Cancel a specific task in a graph."""
        ok = coordinator.cancel_task(graph_id, task_id)
        return {"status": "cancelled" if ok else "not_found"}

    # --- Model Router ---

    @app.get("/api/models/routing")
    async def get_routing_table():
        """Get the model routing table."""
        return {"routing": model_router.get_routing_table()}

    @app.post("/api/models/routing")
    async def update_routing(req: dict):
        """Assign a model to an agent in the routing table."""
        agent = req.get("agent", "")
        model = req.get("model", "")
        if agent and model:
            model_router.assign_model(agent, model)
            return {"status": "updated", "agent": agent, "model": model}
        raise HTTPException(400, "agent and model required")

    # --- Message Bus ---

    @app.get("/api/bus/history")
    async def get_bus_history(limit: int = 50, msg_type: str = None):
        """Get message bus history."""
        from agents.message_bus import MessageType
        mt = MessageType(msg_type) if msg_type else None
        return {"messages": message_bus.get_history(limit, mt)}

    @app.post("/api/bus/publish")
    async def publish_message(req: dict):
        """Publish a message to the bus (debug)."""
        from agents.message_bus import Message, MessageType
        msg = Message(
            msg_type=MessageType(req.get("type", "log")),
            sender=req.get("sender", "api"),
            recipient=req.get("recipient", "*"),
            payload=req.get("payload", {}),
        )
        await message_bus.publish(msg)
        return {"status": "published", "message_id": msg.id}

    # --- Workflows (Automation) ---

    @app.get("/api/workflows")
    async def list_workflows():
        """List all automation workflows."""
        agent = coordinator.agents.get("automation_agent")
        if agent:
            import inspect
            if hasattr(agent, '_list_workflows'):
                result = await agent._list_workflows()
                return result
        return {"workflows": []}

    @app.post("/api/workflows")
    async def create_workflow(req: dict):
        """Create a new automation workflow."""
        agent = coordinator.agents.get("automation_agent")
        if not agent:
            raise HTTPException(500, "Automation agent not available")
        result = await agent._create_workflow(req)
        return result

    @app.post("/api/workflows/{workflow_id}/run")
    async def run_workflow(workflow_id: str):
        """Run a workflow immediately."""
        agent = coordinator.agents.get("automation_agent")
        if not agent:
            raise HTTPException(500, "Automation agent not available")
        result = await agent._run_workflow({"workflow_id": workflow_id})
        return result

    # --- Scheduler ---

    @app.get("/api/scheduler/tasks")
    async def list_scheduled():
        """List all scheduled tasks."""
        agent = coordinator.agents.get("automation_agent")
        if agent and hasattr(agent, '_list_scheduled'):
            return await agent._list_scheduled()
        return {"scheduled_tasks": []}

    @app.post("/api/scheduler/tasks")
    async def schedule_task(req: dict):
        """Schedule a new task."""
        agent = coordinator.agents.get("automation_agent")
        if not agent:
            raise HTTPException(500, "Automation agent not available")
        result = await agent._schedule_task(req)
        return result

    # --- Coordinator Status ---

    @app.get("/api/coordinator/status")
    async def coordinator_status():
        """Get coordinator summary."""
        return coordinator.get_status_summary()

    @app.get("/api/coordinator/events")
    async def coordinator_events(limit: int = 100):
        """Get coordinator event log."""
        return {"events": coordinator.get_event_log(limit)}

    # --- Vector Memory ---

    @app.get("/api/vector-memory/stats")
    async def vector_memory_stats():
        """Get vector memory statistics."""
        return {"stats": vector_memory.get_stats()}

    @app.post("/api/vector-memory/search")
    async def vector_memory_search(req: dict):
        """Search vector memory."""
        query = req.get("query", "")
        k = req.get("k", 5)
        namespace = req.get("namespace")
        results = vector_memory.search(query, k, namespace)
        return {"results": results}

    @app.post("/api/vector-memory/add")
    async def vector_memory_add(req: dict):
        """Add to vector memory."""
        text = req.get("text", "")
        metadata = req.get("metadata", {})
        namespace = req.get("namespace", "default")
        doc_id = vector_memory.add(text, metadata, namespace)
        return {"id": doc_id, "status": "added"}


    # ============================================================
    # Phase 3: Structured Tool System Endpoints
    # ============================================================

    @app.get("/api/tools")
    async def list_tools():
        """List all registered tools with their schemas."""
        return {"tools": tool_registry.get_all_schemas()}

    @app.get("/api/tools/{tool_name}")
    async def get_tool(tool_name: str):
        """Get schema for a specific tool."""
        schema = tool_registry.get_schema(tool_name)
        if not schema:
            raise HTTPException(404, f"Tool '{tool_name}' not found")
        return {"tool": schema.to_dict()}

    @app.post("/api/tools/register")
    async def register_tool(req: dict):
        """Register a new tool schema."""
        from tools.schemas import ToolSchema, ToolAction, ToolParameter, PermissionLevel
        actions = [
            ToolAction(
                name=a["name"],
                description=a.get("description", ""),
                parameters=[ToolParameter(**p) for p in a.get("parameters", [])],
                permission_level=PermissionLevel(a.get("permission_level", "safe")),
                permission_reason=a.get("permission_reason", ""),
            )
            for a in req.get("actions", [])
        ]
        schema = ToolSchema(
            tool_name=req["tool_name"],
            description=req.get("description", ""),
            actions=actions,
            default_permission=PermissionLevel(req.get("default_permission", "safe")),
        )
        from tools.registry import get_registry
        get_registry().register_tool(schema, lambda **kw: {"status": "registered"})
        return {"status": "registered", "tool_name": req["tool_name"]}

    @app.get("/api/tools/activity")
    async def get_tool_activity(limit: int = 100):
        """Get recent tool call history from event bus."""
        events = background_daemon.event_bus.get_history(limit, "tool.executed")
        return {"activity": events}

    # ============================================================
    # Phase 2: Background Daemon Endpoints
    # ============================================================

    @app.get("/api/background/status")
    async def background_status():
        """Get background daemon status."""
        return background_daemon.get_status()

    @app.post("/api/background/restart")
    async def restart_background():
        """Restart background daemon."""
        await background_daemon.stop()
        await background_daemon.start()
        return {"status": "restarted"}

    # --- Event Bus ---

    @app.get("/api/events")
    async def get_events(limit: int = 100, type: str = None):
        """Get event bus history."""
        return {"events": background_daemon.event_bus.get_history(limit, type)}

    @app.post("/api/events/publish")
    async def publish_event(req: dict):
        """Publish an event to the bus."""
        await background_daemon.event_bus.publish(Event(
            type=req.get("type", "manual"),
            payload=req.get("payload", {}),
            sender=req.get("sender", "api"),
            priority=EventPriority[req.get("priority", "NORMAL").upper()],
        ))
        return {"status": "published"}

    # --- Scheduler ---

    @app.get("/api/scheduler/tasks")
    async def list_scheduled_tasks():
        """List all scheduled tasks."""
        return {"tasks": background_daemon.scheduler.get_tasks()}

    @app.post("/api/scheduler/tasks")
    async def create_scheduled_task(req: dict):
        """Create a scheduled task."""
        task = ScheduledTask(
            name=req.get("name", "Unnamed"),
            cron_expr=req.get("cron_expr", ""),
            interval_seconds=req.get("interval_seconds", 0),
            handler=lambda: logger.info(f"Scheduled task '{req.get('name')}' triggered"),
            enabled=req.get("enabled", True),
        )
        task_id = background_daemon.scheduler.add_task(task)
        return {"status": "created", "id": task_id}

    @app.delete("/api/scheduler/tasks/{task_id}")
    async def delete_scheduled_task(task_id: str):
        """Delete a scheduled task."""
        ok = background_daemon.scheduler.remove_task(task_id)
        if not ok:
            raise HTTPException(404, "Task not found")
        return {"status": "deleted"}

    @app.post("/api/scheduler/tasks/{task_id}/toggle")
    async def toggle_scheduled_task(task_id: str, req: dict = None):
        """Enable/disable a scheduled task."""
        task = background_daemon.scheduler.get_task(task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        enabled = req.get("enabled", True) if req else True
        all_tasks = background_daemon.scheduler.get_tasks()
        for t in all_tasks:
            if t["id"] == task_id:
                pass
        return {"status": "toggled", "enabled": enabled}

    # --- Observers ---

    @app.get("/api/observers")
    async def list_observers():
        """List all registered observers."""
        return {"observers": background_daemon.observers.get_observers()}

    @app.post("/api/observers/{name}/toggle")
    async def toggle_observer(name: str, req: dict):
        """Enable/disable an observer."""
        enabled = req.get("enabled", True)
        ok = background_daemon.observers.set_enabled(name, enabled)
        if not ok:
            raise HTTPException(404, f"Observer '{name}' not found")
        return {"status": "toggled", "enabled": enabled}

    # --- Notifications ---

    @app.get("/api/notifications")
    async def get_notifications(limit: int = 50, unread_only: bool = False):
        """Get notifications."""
        return {
            "notifications": background_daemon.notifications.get_notifications(limit, unread_only),
            "unread_count": background_daemon.notifications.get_unread_count(),
        }

    @app.post("/api/notifications/{notif_id}/read")
    async def mark_notification_read(notif_id: str):
        """Mark a notification as read."""
        ok = background_daemon.notifications.mark_read(notif_id)
        if not ok:
            raise HTTPException(404, "Notification not found")
        return {"status": "read"}

    @app.post("/api/notifications/read-all")
    async def mark_all_notifications_read():
        """Mark all notifications as read."""
        background_daemon.notifications.mark_all_read()
        return {"status": "all_read"}

    @app.delete("/api/notifications")
    async def clear_notifications():
        """Clear all notifications."""
        background_daemon.notifications.clear()
        return {"status": "cleared"}

    # --- Task Queue ---

    @app.get("/api/queue/status")
    async def queue_status():
        """Get task queue status."""
        return background_daemon.task_queue.get_status()

    @app.get("/api/queue/completed")
    async def queue_completed(limit: int = 50):
        """Get completed queue tasks."""
        return {"tasks": background_daemon.task_queue.get_completed(limit)}

    # ============================================================
    # Phase 2: Workflow Engine Endpoints
    # ============================================================

    @app.get("/api/workflows")
    async def list_workflows_v2():
        """List all workflows (Phase 2 engine)."""
        return {"workflows": workflow_engine.get_workflows()}

    @app.post("/api/workflows")
    async def create_workflow_v2(req: dict):
        """Create a new workflow."""
        trigger = WorkflowTrigger(
            type=req.get("trigger", {}).get("type", "manual"),
            event_type=req.get("trigger", {}).get("event_type", ""),
            cron_expr=req.get("trigger", {}).get("cron_expr", ""),
            condition=req.get("trigger", {}).get("condition", ""),
        )
        steps = [
            WorkflowStep(
                name=s.get("name", f"Step {i}"),
                action=s.get("action", ""),
                params=s.get("params", {}),
                permission_level=s.get("permission_level", "safe"),
                depends_on=s.get("depends_on", []),
            )
            for i, s in enumerate(req.get("steps", []))
        ]
        wf = Workflow(
            name=req.get("name", "Unnamed"),
            description=req.get("description", ""),
            trigger=trigger,
            steps=steps,
            enabled=req.get("enabled", True),
        )
        wf_id = workflow_engine.add_workflow(wf)
        return {"status": "created", "id": wf_id}

    @app.get("/api/workflows/{workflow_id}")
    async def get_workflow_v2(workflow_id: str):
        """Get a specific workflow."""
        wf = workflow_engine.get_workflow(workflow_id)
        if not wf:
            raise HTTPException(404, "Workflow not found")
        return {"workflow": wf}

    @app.delete("/api/workflows/{workflow_id}")
    async def delete_workflow_v2(workflow_id: str):
        """Delete a workflow."""
        ok = workflow_engine.remove_workflow(workflow_id)
        if not ok:
            raise HTTPException(404, "Workflow not found")
        return {"status": "deleted"}

    @app.post("/api/workflows/{workflow_id}/run")
    async def run_workflow_v2(workflow_id: str):
        """Run a workflow immediately."""
        result = await workflow_engine.run_workflow(workflow_id)
        return result

    @app.post("/api/workflows/{workflow_id}/cancel")
    async def cancel_workflow_v2(workflow_id: str):
        """Cancel a running workflow."""
        ok = workflow_engine.cancel_workflow(workflow_id)
        return {"status": "cancelled" if ok else "not_running"}

    # ============================================================
    # Phase 2: Background Agent Endpoints
    # ============================================================

    @app.post("/api/background/suggest")
    async def get_background_suggestion():
        """Generate a background automation suggestion."""
        suggestion = await background_agent.generate_suggestion()
        return {"suggestion": suggestion or "No suggestion available"}

    @app.get("/api/background/suggestions")
    async def list_suggestions(limit: int = 20):
        """List past background agent suggestions from memory."""
        suggestions = memory.get_memories_by_type("suggestion", limit)
        return {"suggestions": suggestions}

    # ============================================================
    # Phase 5: MCP System Endpoints
    # ============================================================

    @app.get("/api/mcp/servers")
    async def list_mcp_servers():
        """List all MCP servers."""
        return {"servers": mcp_manager.get_all_servers()}

    @app.post("/api/mcp/servers/connect")
    async def connect_mcp_server(req: dict):
        """Connect to an MCP server."""
        name = req.get("name", "")
        if not name:
            raise HTTPException(400, "name required")
        result = await mcp_manager.connect_server(name)
        return result

    @app.post("/api/mcp/servers/disconnect")
    async def disconnect_mcp_server(req: dict):
        """Disconnect from an MCP server."""
        name = req.get("name", "")
        ok = await mcp_manager.disconnect_server(name)
        return {"status": "disconnected" if ok else "not_found"}

    @app.post("/api/mcp/servers/register")
    async def register_mcp_server(req: dict):
        """Register a new MCP server configuration."""
        config = MCPServerConfig(
            name=req.get("name", ""),
            command=req.get("command", ""),
            args=req.get("args", []),
            url=req.get("url", ""),
            transport=req.get("transport", "stdio"),
            env=req.get("env", {}),
            trusted=req.get("trusted", False),
            auto_start=req.get("auto_start", False),
        )
        result = mcp_manager.add_server_config(config)
        return result

    @app.delete("/api/mcp/servers/{name}")
    async def remove_mcp_server(name: str):
        """Remove an MCP server."""
        ok = mcp_manager.remove_server(name)
        return {"status": "removed" if ok else "not_found"}

    @app.post("/api/mcp/servers/{name}/trust")
    async def trust_mcp_server(name: str):
        """Trust an MCP server."""
        mcp_manager.trust_server(name)
        return {"status": "trusted", "name": name}

    @app.post("/api/mcp/servers/{name}/untrust")
    async def untrust_mcp_server(name: str):
        """Untrust an MCP server."""
        mcp_manager.untrust_server(name)
        return {"status": "untrusted", "name": name}

    @app.get("/api/mcp/tools")
    async def list_mcp_tools():
        """List all tools from connected MCP servers."""
        return {"tools": mcp_manager.get_all_mcp_tools()}

    @app.post("/api/mcp/tools/call")
    async def call_mcp_tool(req: dict):
        """Call an MCP tool directly."""
        server_name = req.get("server_name", "")
        tool_name = req.get("tool_name", "")
        args = req.get("args", {})
        from mcp.registry import get_mcp_registry
        client = get_mcp_registry().get_server(server_name)
        if not client:
            raise HTTPException(404, f"Server '{server_name}' not found")
        result = await client.call_tool(tool_name, args)
        return result

    @app.get("/api/mcp/discover")
    async def discover_mcp_servers():
        """Discover available MCP servers."""
        return {"common": mcp_manager.discovery.suggest_common_servers()}

    @app.post("/api/mcp/discover/install")
    async def install_discovered_mcp(req: dict):
        """Install a discovered common MCP server."""
        server_type = req.get("type", "")
        config = COMMON_MCP_SERVERS.get(server_type)
        if not config:
            raise HTTPException(404, f"Unknown server type: {server_type}")
        result = await mcp_manager.discovery.register_and_connect(config)
        return result

    # ============================================================
    # Phase 6: Coding System Endpoints
    # ============================================================

    @app.post("/api/coding/index")
    async def index_project(req: dict):
        """Index a project for code intelligence."""
        path = req.get("path", "")
        recursive = req.get("recursive", True)
        index = repo_indexer.index_project(path, recursive)
        if "error" in index:
            raise HTTPException(400, index["error"])
        return index

    @app.get("/api/coding/indexes")
    async def list_indexes():
        """List all indexed projects."""
        return {"projects": repo_indexer.list_indexed_projects()}

    @app.post("/api/coding/search")
    async def search_code(req: dict):
        """Semantic code search."""
        query = req.get("query", "")
        path = req.get("path", "")
        results = semantic_search.search(query, k=req.get("limit", 10))
        return {"query": query, "results": results}

    @app.post("/api/coding/semantic/index")
    async def index_code_semantic(req: dict):
        """Index code documents for semantic search."""
        path = req.get("path", "")
        index = repo_indexer.get_index(path)
        if not index:
            raise HTTPException(400, "Project not indexed")
        docs = []
        for f in index.get("files", []):
            content = repo_indexer.get_file_content(path, f["path"])
            if content:
                docs.append({"path": f["path"], "content": content[:2000]})
        semantic_search.index_documents(docs)
        return {"status": "indexed", "documents": len(docs)}

    @app.post("/api/coding/patch")
    async def create_patch(req: dict):
        """Create a new patch."""
        file_path = req.get("file_path", "")
        new_content = req.get("new_content", "")
        description = req.get("description", "")
        old_content = ""
        if Path(file_path).exists():
            old_content = Path(file_path).read_text(encoding="utf-8")
        patch = patch_engine.create_patch(file_path, old_content, new_content, description)
        return {"patch": patch.to_dict()}

    @app.get("/api/coding/patches")
    async def list_patches():
        """List all pending patches."""
        return {"patches": patch_engine.get_pending_patches()}

    @app.post("/api/coding/patches/{patch_id}/approve")
    async def approve_patch(patch_id: str):
        """Approve a patch."""
        ok = patch_engine.approve_patch(patch_id)
        return {"status": "approved" if ok else "not_found"}

    @app.post("/api/coding/patches/{patch_id}/apply")
    async def apply_patch(patch_id: str):
        """Apply an approved patch."""
        result = patch_engine.apply_patch(patch_id)
        return result

    @app.post("/api/coding/patches/{patch_id}/revert")
    async def revert_patch(patch_id: str):
        """Revert an applied patch."""
        result = patch_engine.revert_patch(patch_id)
        return result

    @app.post("/api/coding/validate")
    async def validate_syntax(req: dict):
        """Validate code syntax."""
        code = req.get("code", "")
        language = req.get("language", "python")
        return ast_parser.validate_syntax(code, language)

    @app.get("/api/coding/git/status")
    async def git_status(path: str = ""):
        """Get git repository status."""
        if not path:
            raise HTTPException(400, "path required")
        return git_manager.get_status(path)

    @app.get("/api/coding/git/log")
    async def git_log(path: str = "", max_count: int = 20):
        """Get git commit log."""
        if not path:
            raise HTTPException(400, "path required")
        return {"commits": git_manager.get_log(path, max_count)}

    @app.get("/api/coding/git/diff")
    async def git_diff(path: str = "", target: str = "HEAD"):
        """Get git diff."""
        if not path:
            raise HTTPException(400, "path required")
        return {"diff": git_manager.get_diff(path, target)}

    @app.post("/api/coding/git/commit")
    async def git_commit(req: dict):
        """Create a git commit."""
        path = req.get("path", "")
        message = req.get("message", "JARVIS auto-commit")
        if not path:
            raise HTTPException(400, "path required")
        return git_manager.create_commit(path, message)

    @app.post("/api/coding/git/branch")
    async def git_create_branch(req: dict):
        """Create a git branch."""
        path = req.get("path", "")
        branch = req.get("branch", "")
        if not path or not branch:
            raise HTTPException(400, "path and branch required")
        return git_manager.create_branch(path, branch)

    @app.post("/api/coding/deps")
    async def analyze_dependencies(req: dict):
        """Analyze project dependencies."""
        path = req.get("path", "")
        if not path:
            raise HTTPException(400, "path required")
        return dep_analyzer.analyze(path)

    @app.get("/api/coding/deps/graph")
    async def dependency_graph(path: str = ""):
        """Build dependency graph."""
        if not path:
            raise HTTPException(400, "path required")
        return dep_analyzer.build_dependency_graph(path)

    @app.get("/api/coding/workspaces")
    async def list_workspaces():
        """List coding workspaces."""
        return {"workspaces": workspace_manager.list_workspaces()}

    @app.post("/api/coding/workspaces")
    async def create_workspace(req: dict):
        """Create a coding workspace."""
        ws = workspace_manager.create_workspace(
            req.get("name", ""), req.get("path", ""), req.get("description", ""),
        )
        return {"workspace": ws}

    @app.delete("/api/coding/workspaces/{ws_id}")
    async def delete_workspace(ws_id: str):
        """Delete a workspace."""
        ok = workspace_manager.delete_workspace(ws_id)
        return {"status": "deleted" if ok else "not_found"}

    @app.get("/api/coding/memory/stats")
    async def code_memory_stats():
        """Get code memory statistics."""
        return code_memory.get_stats()

    # ============================================================
    # Phase 7: Vision System Endpoints
    # ============================================================

    @app.post("/api/vision/capture")
    async def capture_screen(req: dict = None):
        """Capture the screen."""
        mode = req.get("mode", "full") if req else "full"
        if mode == "window":
            result = screen_capture.capture_active_window()
        elif mode == "region":
            result = screen_capture.capture_region(
                req.get("left", 0), req.get("top", 0),
                req.get("width", 800), req.get("height", 600),
            )
        else:
            result = screen_capture.capture_full_screen()
        if not result:
            raise HTTPException(500, "Screen capture failed")
        return result

    @app.get("/api/vision/screenshots")
    async def list_screenshots(limit: int = 20):
        """List screenshot history."""
        return {"screenshots": screen_capture.get_capture_history(limit)}

    @app.get("/api/vision/screenshots/{capture_id}")
    async def get_screenshot(capture_id: str):
        """Get a screenshot by ID."""
        import os
        from fastapi.responses import FileResponse
        path = Path.home() / ".jarvis" / "screenshots" / f"{capture_id}.png"
        if not path.exists():
            raise HTTPException(404, "Screenshot not found")
        return FileResponse(str(path), media_type="image/png")

    @app.delete("/api/vision/screenshots/{capture_id}")
    async def delete_screenshot(capture_id: str):
        """Delete a screenshot."""
        ok = screen_capture.delete_capture(capture_id)
        return {"status": "deleted" if ok else "not_found"}

    @app.post("/api/vision/ocr")
    async def extract_text(req: dict):
        """Extract text from an image using OCR."""
        image_path = req.get("image_path", "")
        if not image_path:
            raise HTTPException(400, "image_path required")
        text = ocr_engine.extract_text(image_path)
        boxes = ocr_engine.extract_text_with_boxes(image_path)
        return {"text": text, "boxes": boxes}

    @app.post("/api/vision/analyze")
    async def analyze_image(req: dict):
        """Analyze an image (basic info or LLM-based)."""
        image_path = req.get("image_path", "")
        prompt = req.get("prompt", "Describe this image in detail.")
        if not image_path:
            raise HTTPException(400, "image_path required")
        analysis = await image_analyzer.analyze_image(image_path, prompt)
        return {"analysis": analysis}

    @app.post("/api/vision/ui-detect")
    async def detect_ui_elements(req: dict):
        """Detect UI elements in a screenshot."""
        image_path = req.get("image_path", "")
        if not image_path:
            raise HTTPException(400, "image_path required")
        elements = ui_detector.detect_elements(image_path)
        errors = ui_detector.detect_errors(image_path)
        return {"elements": elements, "errors": errors}

    @app.get("/api/vision/context")
    async def get_desktop_context():
        """Get current desktop context."""
        ctx = desktop_context.get_last_context()
        if not ctx:
            return {"context": None, "interpretation": "No context captured yet"}
        interpretation = desktop_context.interpret_context()
        return {"context": ctx, "interpretation": interpretation}

    @app.post("/api/vision/context/refresh")
    async def refresh_desktop_context():
        """Refresh and build desktop context."""
        ctx = await desktop_context.build_context(include_screenshot=True, include_ocr=True)
        interpretation = desktop_context.interpret_context(ctx)
        return {"context": ctx, "interpretation": interpretation}

    @app.get("/api/vision/memory")
    async def get_visual_memory(limit: int = 20):
        """Get visual memory entries."""
        return {"entries": visual_memory.get_recent(limit), "stats": visual_memory.get_stats()}

    @app.post("/api/vision/memory")
    async def store_visual_memory(req: dict):
        """Store a visual memory entry."""
        image_path = req.get("image_path", "")
        summary = req.get("summary", "")
        vid = visual_memory.store(image_path, summary, req.get("metadata"))
        return {"id": vid, "status": "stored"}

    @app.delete("/api/vision/memory/{vid}")
    async def delete_visual_memory(vid: str):
        """Delete a visual memory entry."""
        ok = visual_memory.delete(vid)
        return {"status": "deleted" if ok else "not_found"}

    @app.get("/api/vision/windows")
    async def list_windows():
        """List open windows."""
        return {"windows": window_tracker.list_windows(), "active": window_tracker.get_active_window()}

    @app.get("/api/vision/status")
    async def vision_status():
        """Get vision system status."""
        return {
            "ocr_available": ocr_engine.is_available(),
            "screen_capture_enabled": True,
            "screenshot_count": len(screen_capture.get_capture_history()),
            "visual_memory_entries": visual_memory.get_stats(),
        }


    # ============================================================
    # Phase 8: Browser Worker Endpoints
    # ============================================================

    @app.get("/api/browser/sessions")
    async def list_browser_sessions():
        """List all browser sessions."""
        return browser_manager.get_status()

    @app.post("/api/browser/sessions")
    async def create_browser_session(req: dict = None):
        """Create a new browser session."""
        headless = req.get("headless", False) if req else False
        session = await browser_manager.create_session(headless=headless)
        return {
            "session_id": session.session_id,
            "pages": len(session.pages),
            "active_page": session.active_page_id,
        }

    @app.post("/api/browser/sessions/{session_id}/goto")
    async def browser_goto(session_id: str, req: dict):
        """Navigate to a URL."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page_id = req.get("page_id")
        url = await session.goto(req.get("url", ""), page_id)
        browser_task_memory.log_action(session_id, "goto", req, {"url": url})
        info = await get_page_info(await session.get_active_page())
        return {"url": url, "page_info": info}

    @app.post("/api/browser/sessions/{session_id}/click")
    async def browser_click(session_id: str, req: dict):
        """Click an element on the page."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        result = await click_element(page, req.get("selector"), req.get("text"), req.get("xpath"))
        browser_task_memory.log_action(session_id, "click", req, result)
        return result

    @app.post("/api/browser/sessions/{session_id}/fill")
    async def browser_fill(session_id: str, req: dict):
        """Fill a form field."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        if req.get("fields"):
            result = await fill_form_fields(page, req["fields"])
        else:
            result = await fill_form(page, req.get("selector", ""), req.get("value", ""))
        browser_task_memory.log_action(session_id, "fill", req, result)
        return {"results": result}

    @app.post("/api/browser/sessions/{session_id}/screenshot")
    async def browser_screenshot(session_id: str):
        """Take a screenshot of the current page."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        from fastapi.responses import Response
        img_bytes = await take_screenshot(page)
        browser_task_memory.log_action(session_id, "screenshot", {}, {"size": len(img_bytes)})
        return Response(content=img_bytes, media_type="image/png")

    @app.get("/api/browser/sessions/{session_id}/page")
    async def browser_page_info(session_id: str):
        """Get current page info."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        info = await get_page_info(page)
        info["visible_text"] = (await get_visible_text(page))[:2000]
        return info

    @app.post("/api/browser/sessions/{session_id}/summarize")
    async def browser_summarize(session_id: str):
        """Summarize the current page."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        summary = await summarize_page(page)
        browser_task_memory.log_action(session_id, "summarize", {}, summary)
        return summary

    @app.post("/api/browser/sessions/{session_id}/scrape")
    async def browser_scrape(session_id: str, req: dict = None):
        """Safely scrape visible content."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        selectors = req.get("selectors") if req else None
        data = await safe_scrape(page, selectors)
        browser_task_memory.log_action(session_id, "scrape", {"selectors": selectors}, {"size": len(str(data))})
        return data

    @app.post("/api/browser/sessions/{session_id}/test-links")
    async def browser_test_links(session_id: str):
        """Test all links on the page."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        results = await test_links(page)
        browser_task_memory.log_action(session_id, "test_links", {}, {"count": len(results)})
        return {"results": results}

    @app.post("/api/browser/sessions/{session_id}/seo-audit")
    async def browser_seo_audit(session_id: str):
        """Run a basic SEO audit on the page."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        audit = await seo_audit(page)
        browser_task_memory.log_action(session_id, "seo_audit", {}, audit)
        return audit

    @app.get("/api/browser/sessions/{session_id}/links")
    async def browser_links(session_id: str):
        """Get all links on the page."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        links = await get_links(page)
        return {"links": links}

    @app.get("/api/browser/sessions/{session_id}/forms")
    async def browser_forms(session_id: str):
        """Get all forms on the page."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        forms = await get_forms(page)
        return {"forms": forms}

    @app.post("/api/browser/sessions/{session_id}/fill-form-safe")
    async def browser_fill_form_safe(session_id: str, req: dict):
        """Fill a form with safety checks."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        form_idx = req.get("form_index", 0)
        values = req.get("values", {})
        approved = req.get("approved", False)
        forms = await get_forms(page)
        if form_idx >= len(forms):
            raise HTTPException(400, "Form index out of range")
        result = await fill_form_safe(page, forms[form_idx], values, approved)
        browser_task_memory.log_action(session_id, "fill_form", req, result)
        return result

    @app.post("/api/browser/sessions/{session_id}/check-element")
    async def browser_check_element(session_id: str, req: dict):
        """Check if an element exists on the page."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page = await session.get_active_page()
        return await check_element(page, req.get("selector"), req.get("text"))

    @app.post("/api/browser/sessions/{session_id}/new-page")
    async def browser_new_page(session_id: str):
        """Open a new tab/page."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        page_id = await session.new_page()
        return {"page_id": page_id}

    @app.delete("/api/browser/sessions/{session_id}")
    async def close_browser_session(session_id: str):
        """Close a browser session."""
        await browser_manager.close_session(session_id)
        return {"status": "closed"}

    @app.delete("/api/browser/sessions")
    async def close_all_browser_sessions():
        """Close all browser sessions."""
        await browser_manager.close_all()
        return {"status": "all_closed"}

    @app.get("/api/browser/history")
    async def browser_action_history(session_id: str = None, limit: int = 100):
        """Get browser action history."""
        return {"actions": browser_task_memory.get_action_history(session_id, limit)}

    @app.post("/api/browser/uptime")
    async def browser_check_uptime(req: dict):
        """Check website uptime."""
        url = req.get("url", "")
        if not url:
            raise HTTPException(400, "url required")
        result = await check_uptime(url)
        return result

    @app.get("/api/browser/login-sessions")
    async def browser_login_sessions():
        """Get saved login sessions."""
        return {"sessions": browser_task_memory.get_login_sessions()}

    @app.post("/api/browser/sessions/{session_id}/replay")
    async def browser_replay(session_id: str):
        """Replay recorded actions for a session."""
        session = await browser_manager.get_session(session_id)
        if not session:
            raise HTTPException(404, "Session not found")
        actions = browser_task_memory.get_replay_actions(session_id)
        results = []
        for action in actions:
            page = await session.get_active_page()
            try:
                if action["action"] == "goto":
                    await session.goto(action["params"].get("url", ""))
                elif action["action"] == "click":
                    await click_element(page, action["params"].get("selector"))
                elif action["action"] == "fill":
                    await fill_form(page, action["params"].get("selector", ""), action["params"].get("value", ""))
                results.append({"action": action["action"], "status": "replayed"})
            except Exception as e:
                results.append({"action": action["action"], "status": "failed", "error": str(e)})
        return {"replayed": len(results), "results": results}

    # ============================================================
    # Phase 9: Hybrid Long-Term Memory Endpoints
    # ============================================================

    @app.post("/api/hybrid-memory/add")
    async def hybrid_memory_add(req: dict):
        """Add an entry to hybrid memory."""
        result = hybrid_memory.add(
            memory_type=req.get("type", "task"),
            content=req.get("content", ""),
            metadata=req.get("metadata", {}),
            project=req.get("project", ""),
            importance=req.get("importance", 1),
        )
        return result

    @app.post("/api/hybrid-memory/search")
    async def hybrid_memory_search(req: dict):
        """Semantic search in hybrid memory."""
        results = hybrid_memory.semantic_search(
            query=req.get("query", ""),
            memory_type=req.get("type"),
            limit=req.get("limit", 20),
        )
        return {"results": results}

    @app.get("/api/hybrid-memory/entries")
    async def hybrid_memory_list(type: str = None, project: str = None, limit: int = 50):
        """List hybrid memory entries."""
        if type:
            entries = hybrid_memory.get_by_type(type, project, limit)
        elif project:
            entries = hybrid_memory.get_by_project(project, limit)
        else:
            entries = hybrid_memory.get_timeline(limit=limit)
        return {"entries": entries, "total": hybrid_memory.count(type)}

    @app.get("/api/hybrid-memory/entry/{entry_id}")
    async def hybrid_memory_get(entry_id: str):
        """Get a specific hybrid memory entry."""
        entry = hybrid_memory.get(entry_id)
        if not entry:
            raise HTTPException(404, "Entry not found")
        return entry

    @app.put("/api/hybrid-memory/entry/{entry_id}")
    async def hybrid_memory_update(entry_id: str, req: dict):
        """Update a hybrid memory entry."""
        ok = hybrid_memory.update(
            entry_id,
            content=req.get("content"),
            metadata=req.get("metadata"),
            importance=req.get("importance"),
        )
        if not ok:
            raise HTTPException(404, "Entry not found")
        return {"status": "updated"}

    @app.delete("/api/hybrid-memory/entry/{entry_id}")
    async def hybrid_memory_delete(entry_id: str):
        """Delete a hybrid memory entry."""
        ok = hybrid_memory.delete(entry_id)
        return {"status": "deleted" if ok else "not_found"}

    @app.delete("/api/hybrid-memory")
    async def hybrid_memory_clear(type: str = None):
        """Clear hybrid memory."""
        hybrid_memory.clear(type)
        return {"status": "cleared"}

    @app.get("/api/hybrid-memory/export")
    async def hybrid_memory_export(type: str = None, project: str = None):
        """Export hybrid memory."""
        entries = hybrid_memory.export(type, project)
        return {"entries": entries, "count": len(entries)}

    @app.post("/api/hybrid-memory/import")
    async def hybrid_memory_import(req: dict):
        """Import entries into hybrid memory."""
        entries = req.get("entries", [])
        hybrid_memory.import_entries(entries)
        return {"imported": len(entries)}

    @app.post("/api/hybrid-memory/cleanup")
    async def hybrid_memory_cleanup(req: dict = None):
        """Cleanup old low-importance memories."""
        days = req.get("days", 90) if req else 90
        hybrid_memory.cleanup_old(days)
        return {"status": "cleaned", "older_than_days": days}

    @app.get("/api/hybrid-memory/projects")
    async def hybrid_memory_projects():
        """List all projects in hybrid memory."""
        return {"projects": hybrid_memory.get_projects()}

    @app.get("/api/hybrid-memory/categories")
    async def hybrid_memory_categories():
        """Get memory category counts."""
        from memory.hybrid_memory import MEMORY_TYPES
        counts = {t: hybrid_memory.count(t) for t in MEMORY_TYPES}
        return {"categories": counts}

    @app.post("/api/hybrid-memory/timeline")
    async def hybrid_memory_timeline(req: dict = None):
        """Get memory timeline."""
        days = req.get("days", 7) if req else 7
        memory_type = req.get("type") if req else None
        entries = hybrid_memory.get_timeline(days, memory_type)
        return {"entries": entries, "days": days}

    # ============================================================
    # Phase 10: Learning System Endpoints
    # ============================================================

    @app.post("/api/learning/failure/record")
    async def learning_record_failure(req: dict):
        """Record a failure for analysis."""
        entry = failure_analyzer.record_failure(
            action=req.get("action", ""),
            tool=req.get("tool", ""),
            error=req.get("error", ""),
            context=req.get("context", ""),
            task_id=req.get("task_id", ""),
        )
        return entry

    @app.get("/api/learning/failures")
    async def learning_list_failures(limit: int = 100):
        """List recorded failures."""
        return {"failures": failure_analyzer.get_all(limit), "patterns": failure_analyzer.get_patterns()}

    @app.get("/api/learning/suggestions")
    async def learning_suggestions():
        """Get avoidance suggestions based on failures."""
        return {"suggestions": failure_analyzer.get_avoidance_suggestions()}

    @app.post("/api/learning/workflow/record")
    async def learning_record_workflow(req: dict):
        """Record a workflow execution for learning."""
        entry = workflow_learner.record_workflow(
            steps=req.get("steps", []),
            source=req.get("source", ""),
        )
        return entry

    @app.get("/api/learning/workflows/recent")
    async def learning_recent_workflows(limit: int = 50):
        """Get recent workflow records."""
        return {"workflows": workflow_learner.get_recent(limit)}

    @app.get("/api/learning/automation-suggestions")
    async def learning_automation_suggestions():
        """Get automation suggestions from workflow patterns."""
        return {"suggestions": workflow_learner.suggest_automations(), "patterns": workflow_learner.get_repeatable_patterns()}

    @app.get("/api/learning/workflow-stats")
    async def learning_workflow_stats():
        """Get workflow learning statistics."""
        return workflow_learner.get_stats()

    @app.post("/api/learning/prompt/record")
    async def learning_record_prompt(req: dict):
        """Record a prompt for optimization."""
        entry = prompt_optimizer.record_prompt(
            prompt=req.get("prompt", ""),
            context=req.get("context", ""),
            task_type=req.get("task_type", ""),
            outcome=req.get("outcome", "unknown"),
            response_quality=req.get("response_quality", 0.5),
        )
        return entry

    @app.post("/api/learning/prompt/optimize")
    async def learning_optimize_prompt(req: dict):
        """Optimize a prompt based on past successes."""
        optimized = prompt_optimizer.optimize_prompt(
            prompt=req.get("prompt", ""),
            task_type=req.get("task_type", ""),
        )
        return {"original": req.get("prompt", ""), "optimized": optimized}

    @app.get("/api/learning/prompt/templates")
    async def learning_prompt_templates():
        """Get saved prompt templates."""
        return {"templates": prompt_optimizer.get_all_templates()}

    @app.post("/api/learning/prompt/templates")
    async def learning_save_template(req: dict):
        """Save a prompt template."""
        prompt_optimizer.save_template(req.get("name", ""), req.get("template", ""))
        return {"status": "saved"}

    @app.get("/api/learning/recommendations")
    async def learning_recommendations():
        """Get skill/tool recommendations."""
        return {"recommendations": recommendation_engine.get_recommendations()}

    @app.post("/api/learning/recommendations/dismiss")
    async def learning_dismiss_recommendation(req: dict):
        """Dismiss a recommendation."""
        recommendation_engine.dismiss(req.get("id", ""))
        return {"status": "dismissed"}

    @app.post("/api/learning/usage/log")
    async def learning_log_usage(req: dict):
        """Log skill/tool usage for recommendations."""
        entry = recommendation_engine.log_usage(
            category=req.get("category", ""),
            item=req.get("item", ""),
            context=req.get("context", ""),
        )
        return entry

    @app.get("/api/learning/usage/stats")
    async def learning_usage_stats():
        """Get usage statistics."""
        return recommendation_engine.get_usage_stats()

    @app.post("/api/learning/correction/record")
    async def learning_record_correction(req: dict):
        """Record a user correction."""
        entry = correction_tracker.record_correction(
            action=req.get("action", ""),
            correction=req.get("correction", ""),
            context=req.get("context", ""),
        )
        return entry

    @app.get("/api/learning/corrections")
    async def learning_corrections(limit: int = 50):
        """Get recorded corrections."""
        return {
            "corrections": correction_tracker.get_corrections(limit),
            "recurring": correction_tracker.get_recurring_issues(),
            "banned_patterns": correction_tracker.get_banned_patterns(),
        }

    # ============================================================
    # Phase 11: Advanced Model Router Endpoints
    # ============================================================

    @app.get("/api/models/router-status")
    async def router_status():
        """Get model router status."""
        return model_router.get_status()

    @app.post("/api/models/analyze-task")
    async def router_analyze_task(req: dict):
        """Analyze a task and recommend the best model."""
        decision = model_router.get_routing_decision(
            task=req.get("task", ""),
            agent_name=req.get("agent_name", ""),
        )
        return decision

    @app.post("/api/models/force")
    async def router_force_model(req: dict):
        """Force a specific model for all requests."""
        model = req.get("model", "")
        if model:
            model_router.force_model(model)
            return {"status": "forced", "model": model}
        raise HTTPException(400, "model required")

    @app.post("/api/models/release-force")
    async def router_release_force():
        """Release the forced model override."""
        model_router.release_force()
        return {"status": "released"}

    @app.post("/api/models/disable")
    async def router_disable_model(req: dict):
        """Disable a specific model."""
        model_router.disable_model(req.get("model", ""))
        return {"status": "disabled"}

    @app.post("/api/models/enable")
    async def router_enable_model(req: dict):
        """Enable a previously disabled model."""
        model_router.enable_model(req.get("model", ""))
        return {"status": "enabled"}

    @app.get("/api/models/health")
    async def router_health():
        """Get model health summary."""
        return model_router.health.get_summary()

    @app.get("/api/models/health/{model_name}")
    async def router_model_health(model_name: str):
        """Get health for a specific model."""
        return model_router.health.get_health(model_name)

    @app.post("/api/models/balancer/strategy")
    async def router_balancer_strategy(req: dict):
        """Set load balancer strategy."""
        model_router.set_balancer_strategy(req.get("strategy", "least_load"))
        return {"status": "set", "strategy": req.get("strategy")}

    @app.get("/api/models/installed")
    async def router_installed_models():
        """Get installed models with capabilities."""
        return {"models": model_router.registry.get_installed_list()}

    @app.post("/api/models/warm-up")
    async def router_warm_up(req: dict):
        """Warm up a model for faster first response."""
        await model_router.warm_up(req.get("model", ""))
        return {"status": "warming"}

    @app.get("/api/models/fallback-chains")
    async def router_fallback_chains():
        """Get all fallback chains."""
        return model_router.fallback.get_all_chains()

    # ============================================================
    # Phase 12: Desktop Operator Endpoints
    # ============================================================

    @app.get("/api/desktop/state")
    async def desktop_get_state():
        """Get current desktop state."""
        return await app_state_detector.get_desktop_state()

    @app.get("/api/desktop/running-apps")
    async def desktop_running_apps():
        """Get list of running applications."""
        return {"apps": await app_state_detector.get_running_apps()}

    @app.get("/api/desktop/active-window")
    async def desktop_active_window():
        """Get active window information."""
        return await window_manager.get_active_window()

    @app.get("/api/desktop/windows")
    async def desktop_list_windows():
        """List all open windows."""
        return {"windows": await window_manager.list_windows()}

    @app.post("/api/desktop/windows/focus")
    async def desktop_focus_window(req: dict):
        """Focus a window by title."""
        ok = await window_manager.focus_window(req.get("title", ""))
        return {"focused": ok}

    @app.post("/api/desktop/windows/minimize")
    async def desktop_minimize_window(req: dict):
        """Minimize a window."""
        ok = await window_manager.minimize_window(req.get("title", ""))
        return {"minimized": ok}

    @app.post("/api/desktop/windows/maximize")
    async def desktop_maximize_window(req: dict):
        """Maximize a window."""
        ok = await window_manager.maximize_window(req.get("title", ""))
        return {"maximized": ok}

    @app.post("/api/desktop/windows/close")
    async def desktop_close_window(req: dict):
        """Close a window."""
        ok = await window_manager.close_window(req.get("title", ""))
        return {"closed": ok}

    @app.post("/api/desktop/mouse/move")
    async def desktop_mouse_move(req: dict):
        """Move the mouse cursor."""
        result = await mouse_controller.move_to(req.get("x", 0), req.get("y", 0))
        return result

    @app.post("/api/desktop/mouse/click")
    async def desktop_mouse_click(req: dict):
        """Click the mouse."""
        result = await mouse_controller.click(
            button=req.get("button", "left"),
            x=req.get("x"), y=req.get("y"),
        )
        return result

    @app.post("/api/desktop/mouse/double-click")
    async def desktop_mouse_double_click(req: dict):
        """Double-click the mouse."""
        result = await mouse_controller.double_click(req.get("x"), req.get("y"))
        return result

    @app.post("/api/desktop/mouse/right-click")
    async def desktop_mouse_right_click(req: dict):
        """Right-click the mouse."""
        result = await mouse_controller.right_click(req.get("x"), req.get("y"))
        return result

    @app.post("/api/desktop/mouse/drag")
    async def desktop_mouse_drag(req: dict):
        """Drag the mouse."""
        result = await mouse_controller.drag(
            req.get("start_x", 0), req.get("start_y", 0),
            req.get("end_x", 0), req.get("end_y", 0),
        )
        return result

    @app.post("/api/desktop/mouse/scroll")
    async def desktop_mouse_scroll(req: dict):
        """Scroll the mouse wheel."""
        result = await mouse_controller.scroll(req.get("clicks", 0))
        return result

    @app.get("/api/desktop/mouse/position")
    async def desktop_mouse_position():
        """Get current mouse position."""
        return await mouse_controller.get_position()

    @app.post("/api/desktop/keyboard/type")
    async def desktop_keyboard_type(req: dict):
        """Type text."""
        result = await keyboard_controller.type_text(req.get("text", ""))
        return result

    @app.post("/api/desktop/keyboard/hotkey")
    async def desktop_keyboard_hotkey(req: dict):
        """Send a hotkey combination."""
        result = await keyboard_controller.hotkey(req.get("keys", ""))
        return result

    @app.post("/api/desktop/keyboard/press")
    async def desktop_keyboard_press(req: dict):
        """Press a specific key."""
        result = await keyboard_controller.press_key(req.get("key", ""), req.get("times", 1))
        return result

    @app.get("/api/desktop/clipboard")
    async def desktop_clipboard_read():
        """Read clipboard contents."""
        text = await clipboard_manager.read_text()
        return {"text": text}

    @app.post("/api/desktop/clipboard")
    async def desktop_clipboard_write(req: dict):
        """Write to clipboard."""
        return await clipboard_manager.write_text(req.get("text", ""))

    @app.post("/api/desktop/clipboard/clear")
    async def desktop_clipboard_clear():
        """Clear clipboard."""
        return await clipboard_manager.clear()

    @app.get("/api/desktop/dialogs")
    async def desktop_detect_dialogs():
        """Detect system dialogs."""
        return {"dialogs": await app_state_detector.detect_dialogs()}

    @app.get("/api/desktop/focused-app")
    async def desktop_focused_app():
        """Get type of focused application."""
        return {"app_type": await app_state_detector.get_focused_app_type()}

    @app.post("/api/desktop/mode")
    async def desktop_set_mode(req: dict):
        """Set desktop assistant mode (safe/developer/autonomous)."""
        mode = req.get("mode", "safe")
        app_state_detector.set_mode(mode)
        return {"mode": mode}

    @app.get("/api/desktop/mode")
    async def desktop_get_mode():
        """Get current desktop assistant mode."""
        return {"mode": app_state_detector.get_mode()}

    @app.post("/api/desktop/launch-app")
    async def desktop_launch_app(req: dict):
        """Launch a desktop application."""
        result = await ui_automation.launch_app(req.get("app_path", ""), req.get("args", ""))
        return result

    @app.post("/api/desktop/screen-text")
    async def desktop_screen_text():
        """Extract text from screen via OCR."""
        text = await ui_automation.get_screen_text()
        return {"text": text}

    @app.post("/api/desktop/click-text")
    async def desktop_click_text(req: dict):
        """Find and click text on screen."""
        result = await ui_automation.click_text(req.get("text", ""), ocr_engine)
        return result

    @app.post("/api/desktop/launch-and-wait")
    async def desktop_launch_and_wait(req: dict):
        """Launch an app and wait for its window."""
        await ui_automation.launch_app(req.get("app_path", ""), req.get("args", ""))
        found = await ui_automation.wait_for_window(req.get("title_pattern", ""), req.get("timeout", 10))
        return {"launched": True, "window_found": found}


# Create app instance for direct import if needed
app = create_app()
