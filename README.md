# JARVIS - Private Local AI Assistant for Windows 10

A private, local-first AI assistant that runs entirely on your Windows 10 PC using Ollama and Qwen models. No cloud dependencies, no data leaks, full privacy.

## Features

- **Chat Interface** - Talk to JARVIS via a futuristic dark-themed UI
- **Voice Control** - Push-to-talk (F4), optional wake word, text-to-speech
- **10+ Skill System** - Extend JARVIS with installable skills (file manager, browser, PowerShell, etc.)
- **Agent System** - Specialized agents for different tasks (coding, research, web, files)
- **Browser Automation** - Playwright-powered web control
- **File Management** - Browse, read, create, edit, search files
- **Coding Workspace** - AI-assisted code editing, testing, debugging
- **Long-term Memory** - SQLite-based persistent memory with search
- **Security** - Permission levels for all actions; asks before dangerous operations
- **System Tray** - Minimizes to tray, starts with Windows option
- **Fully Local** - Works offline; all AI processing via Ollama local models

## Quick Start

### Prerequisites

1. **Ollama** - Install from https://ollama.com
2. **Pull a model**: `ollama pull qwen3` (or `qwen2.5`, `qwen2`)
3. **Python 3.10+** - with `pip`
4. **Node.js 18+** - with `npm`
5. **Playwright** (for browser skill): `pip install playwright && playwright install chromium`

### Installation

```powershell
# 1. Clone or download JARVIS
cd jarvis

# 2. Install Python dependencies
pip install -r backend/requirements.txt

# 3. Install frontend dependencies
cd frontend && npm install && cd ..

# 4. Install Electron dependencies
cd electron && npm install && cd ..

# 5. Copy and configure environment
copy .env.example .env
# Edit .env to set OLLAMA_MODEL to your model (default: qwen3)

# 6. Start JARVIS
# Option A: Full app with Electron
cd electron && npm start

# Option B: Backend only (API)
cd backend && python main.py
# Then open frontend: cd frontend && npm run dev
```

### Configuration

Edit `config/default.json` or use `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama API URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | LLM model name | `qwen3` |
| `MEMORY_ENABLED` | Enable memory | `true` |
| `STT_ENGINE` | Speech-to-text engine | `whisper` |
| `TTS_ENGINE` | Text-to-speech engine | `windows` |
| `PERMISSION_MODE` | Security mode | `ask` |

## Project Structure

```
jarvis/
├── backend/          # Python FastAPI backend
│   ├── agents/       # Agent system & orchestrator
│   ├── api/          # REST API server
│   ├── memory/       # SQLite memory database
│   ├── security/     # Permission management
│   ├── skills_engine/ # Skill discovery & loading
│   ├── voice/        # STT/TTS modules
│   ├── config.py     # Configuration manager
│   ├── main.py       # Backend entry point
│   └── ollama_client.py  # Ollama API client
├── electron/         # Electron desktop shell
│   ├── main/         # Main process (tray, IPC, backend)
│   └── preload/      # Context bridge
├── frontend/         # React UI (Vite)
│   └── src/
│       ├── components/  # Reusable UI components
│       ├── pages/      # All 10 pages
│       ├── hooks/      # Custom React hooks
│       ├── utils/      # API client
│       └── styles/     # CSS theme
├── skills/           # Installed skills
│   ├── app_launcher/
│   ├── browser_playwright/
│   ├── code_editor/
│   ├── file_manager/
│   ├── memory_search/
│   ├── pdf_reader/
│   ├── powershell_runner/
│   ├── screenshot_reader/
│   ├── system_monitor/
│   ├── web_search/
│   └── website_builder/
├── config/
│   └── default.json
├── docs/
├── .env.example
└── README.md
```

## Architecture

```
┌─────────────────────────────────┐
│   Electron Desktop App         │
│   ┌───────────────────────┐    │
│   │  React Frontend       │    │
│   │  (Chat, Voice, etc)   │    │
│   └──────────┬────────────┘    │
│              │ IPC/HTTP         │
│   ┌──────────▼────────────┐    │
│   │  Python Backend       │    │
│   │  (FastAPI)             │    │
│   └──────────┬────────────┘    │
│              │ HTTP             │
│   ┌──────────▼────────────┐    │
│   │  Ollama (Qwen)        │    │
│   │  Local LLM            │    │
│   └───────────────────────┘    │
└─────────────────────────────────┘
```

## Security

JARVIS uses a layered permission system:

| Level | Examples | Behavior |
|-------|----------|----------|
| **Safe** | Read files, search, chat | Auto-allowed |
| **Medium** | Create/edit files, clipboard | Auto-allowed (configurable) |
| **High** | Shell commands, installs, system settings | Asks for confirmation |
| **Critical** | Delete files, payments, send messages | Asks for confirmation |

Set `PERMISSION_MODE=ask` (default), `strict`, or `auto` in `.env`.
See `docs/SECURITY.md` for details.

## Skills

Skills extend JARVIS with new capabilities. Each skill lives in `/skills/<name>/` with:
- `manifest.json` - metadata, permissions, commands
- `skill.py` - Python implementation

**Pre-installed skills:**
- `file_manager` - Browse, read, create, edit files
- `browser_playwright` - Web automation
- `powershell_runner` - Run PowerShell commands (requires permission)
- `screenshot_reader` - Screen capture
- `app_launcher` - Launch applications
- `system_monitor` - CPU/RAM/disk metrics
- `web_search` - DuckDuckGo search
- `code_editor` - Code reading and writing
- `memory_search` - Query JARVIS memory
- `website_builder` - Generate HTML sites
- `pdf_reader` - Extract PDF text

See `docs/SKILL_DEV_GUIDE.md` to create your own skills.

## API

Backend runs at `http://127.0.0.1:8765/api/`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Streaming chat with agent |
| `/models` | GET | List Ollama models |
| `/memory` | GET/POST/DELETE | Manage memory |
| `/skills` | GET | List installed skills |
| `/skills/toggle` | POST | Enable/disable skill |
| `/skills/install` | POST | Install skill |
| `/skills/execute` | POST | Run skill command |
| `/permissions/pending` | GET | Pending approvals |
| `/permissions/respond` | POST | Approve/deny action |
| `/config` | GET/POST | Configuration |
| `/system/info` | GET | System metrics |
| `/shell` | POST | Run PowerShell command |

## Why Local AI?

- **Privacy** - Your data never leaves your PC
- **Free** - No API costs, no subscriptions
- **Offline** - Works without internet
- **Customizable** - Full control over model, skills, behavior
- **Fast** - No network latency for most operations
