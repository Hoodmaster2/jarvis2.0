# JARVIS Multi-Agent Architecture

## Overview

JARVIS Phase 4 transforms the single-agent assistant into a **modular multi-agent AI operating environment** with specialized cooperating agents, shared memory, DAG-based task planning, and safety validation at every step.

## Architecture

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                   Coordinator                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Task     │  │ Priority │  │ Dependency       │  │
│  │ Queue    │  │ Queue    │  │ Tracker          │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │              Message Bus                      │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                   Agents                             │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Planner  │──┤ Executor │──┤ Critic   │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│       │              │              │               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Research │  │ Coding   │  │ Memory   │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│       │                                             │
│  ┌──────────┐                                       │
│  │Automation│                                       │
│  └──────────┘                                       │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│              Shared Memory Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ SQLite   │  │  Vector  │  │  Agent   │          │
│  │(Relational)│ │(Semantic)│ │(Context) │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
```

## Components

### 1. Message Bus (`message_bus.py`)
The communication backbone. All agents communicate through structured messages.

```python
Message {
    id: str,
    type: MessageType (TASK_ASSIGN, TASK_RESULT, OBSERVATION, etc.),
    sender: str,
    recipient: str,
    payload: dict,
    correlation_id: str,
    reply_to: str,
    timestamp: float
}
```

- **Pub/Sub** pattern - agents subscribe to their name or "*" for broadcasts
- **Request/Response** - agents can wait for replies to messages
- **History** - last 1000 messages retained for debugging

### 2. Coordinator (`coordinator.py`)
Central task manager and orchestrator.

Responsibilities:
- **Task Queue** - Priority-based async task queue
- **Dependency Tracking** - Ensures tasks execute in correct order
- **Agent Lifecycle** - Monitors agent states (idle/planning/executing/waiting/failed/completed)
- **Concurrency Control** - Limits parallel execution (configurable max)
- **Event Logging** - Records all coordination events

### 3. Task Graph System (`task_graph.py`)
DAG (Directed Acyclic Graph) for task execution.

```
Research website  ──→  Extract data  ──→  Generate summary
                                              │
                                              ▼
                                      Save memory ──→ Notify user
```

Features:
- **Dependencies** - Tasks wait for their dependencies to complete
- **Retries** - Configurable retry count per task
- **Parallel Branches** - Independent tasks run concurrently
- **Conditional Execution** - Failed tasks block dependents
- **Cancellation** - Cancel individual tasks or entire graphs

### 4. Specialized Agents

| Agent | File | Responsibility |
|-------|------|---------------|
| **Planner** | `planner_agent.py` | Analyzes requests, breaks into steps, assigns agents, prioritizes |
| **Executor** | `executor_agent.py` | Executes approved tool calls, handles retries, returns observations |
| **Critic** | `critic_agent.py` | Validates outputs, detects hallucinations, inspects tool results |
| **Memory** | `memory_agent.py` | Retrieves context, summarizes, stores results, prevents duplicate work |
| **Research** | `research_agent.py` | Web search, deep research, source validation |
| **Coding** | `coding_agent.py` | Project analysis, patch generation, debugging, indexing |
| **Automation** | `automation_agent.py` | Recurring workflows, scheduled tasks, event-driven automation |

### 5. Model Router (`models/router.py`)
Per-agent model assignment and fallback chain.

```python
router.assign_model("coding_agent", "qwen3")
router.assign_model("research_agent", "qwen3")
```

Default routing:
- All agents → `qwen3` (or configured default)
- Embeddings → `nomic-embed-text`

### 6. Vector Memory (`memory/vector_memory.py`)
Semantic memory layer supporting multiple backends.

| Backend | Requirements | Features |
|---------|-------------|----------|
| In-Memory | None (default) | Simple, no persistence |
| ChromaDB | `pip install chromadb` | Persistent, scalable |
| LanceDB | `pip install lancedb` | Fast, columnar |

## Agent Lifecycle

```
                    ┌─────────┐
                    │  IDLE   │
                    └────┬────┘
                         │ Task assigned
                         ▼
                    ┌──────────┐
                    │ PLANNING │
                    └────┬─────┘
                         │ Plan ready
                         ▼
                    ┌───────────┐
              ┌─────│ EXECUTING │─────┐
              │     └───────────┘     │
              │ Success               │ Failure
              ▼                       ▼
        ┌───────────┐          ┌────────┐
        │ COMPLETED │          │ FAILED │
        └───────────┘          └────────┘
                                     │
                              Retry available?
                              Yes ──→ PENDING (retry)
                              No  ──→ stays FAILED
```

## Safety Rules

1. **Executor agents cannot bypass permissions** - All tool calls go through the permission system
2. **Critic validates risky outputs** - Every significant output is validated
3. **Automation cannot execute HIGH/CRITICAL actions autonomously** - Must flag for user approval
4. **Task graphs track all execution** - Full audit trail for every action
5. **Message bus records everything** - Complete communication history

## API Endpoints

### Agent Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents` | List all agents and statuses |
| GET | `/api/agents/{name}` | Get specific agent status |
| POST | `/api/agents/{name}/assign-model` | Assign model to agent |

### Task Graphs
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/graphs/submit` | Submit request for multi-agent processing |
| GET | `/api/graphs` | List all graphs |
| GET | `/api/graphs/{id}` | Get graph details |
| GET | `/api/graphs/{id}/dag` | Get DAG visualization data |
| POST | `/api/graphs/{id}/cancel` | Cancel graph |
| POST | `/api/graphs/{id}/tasks/{tid}/cancel` | Cancel specific task |

### Model Router
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models/routing` | Get routing table |
| POST | `/api/models/routing` | Update routing assignment |

### Message Bus
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/bus/history` | Get message history |
| POST | `/api/bus/publish` | Publish debug message |

### Workflows & Scheduler
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workflows` | List workflows |
| POST | `/api/workflows` | Create workflow |
| POST | `/api/workflows/{id}/run` | Execute workflow |
| GET | `/api/scheduler/tasks` | List scheduled tasks |
| POST | `/api/scheduler/tasks` | Schedule a task |

### Coordinator
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/coordinator/status` | Coordinator summary |
| GET | `/api/coordinator/events` | Event log |

### Vector Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/vector-memory/stats` | Memory statistics |
| POST | `/api/vector-memory/search` | Semantic search |
| POST | `/api/vector-memory/add` | Add to memory |

## Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Agent Dashboard | `/agents` | Agent statuses, task graphs, routing table, event log, request submission |
| Workflow Timeline | `/workflows` | Workflow management, scheduled tasks, workflow creation |

## Example Workflow

1. User submits: "Research the latest AI news and save a summary"
2. **Planner** creates graph:
   - `research_agent.search("latest AI news")` 
   - `memory_agent.store_result(...)` (depends on search)
   - `critic_agent.validate(result)` (depends on search)
3. **Coordinator** executes tasks respecting dependencies
4. **Research Agent** searches the web
5. **Critic** validates the results
6. **Memory Agent** stores the summary
7. Graph marked as completed
8. User notified of results

## File Structure

```
backend/agents/
├── base_agent.py      # Abstract base for all agents
├── message_bus.py     # Agent communication backbone
├── task_graph.py      # DAG task execution system
├── coordinator.py     # Central task manager
├── planner_agent.py   # Request analysis and planning
├── executor_agent.py  # Tool execution with retries
├── critic_agent.py    # Output validation
├── memory_agent.py    # Context and memory management
├── research_agent.py  # Web research
├── coding_agent.py    # Code operations
└── automation_agent.py # Scheduled tasks and workflows

backend/memory/
├── memory_manager.py  # SQLite memory (existing)
└── vector_memory.py   # Semantic vector memory (new)

backend/models/
└── router.py          # Per-agent model routing (new)
```
