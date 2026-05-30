# JARVIS - Windows Setup Guide

## Prerequisites

### 1. Install Ollama
1. Go to https://ollama.com/download/windows
2. Download and run the installer
3. Open a terminal and pull your model:
   ```powershell
   ollama pull qwen3
   ```
   Also pull the embedding model for memory:
   ```powershell
   ollama pull nomic-embed-text
   ```

### 2. Install Python 3.10+
1. Download from https://www.python.org/downloads/
2. **Important**: Check "Add Python to PATH" during installation
3. Verify: `python --version`

### 3. Install Node.js 18+
1. Download from https://nodejs.org/
2. Install with default settings
3. Verify: `node --version` and `npm --version`

### 4. Install Git (optional)
1. Download from https://git-scm.com/download/win
2. Default settings are fine

## Installation Steps

### Step 1: Get JARVIS
```powershell
# Clone (if using git)
git clone <repo-url> jarvis
cd jarvis

# Or download and extract the ZIP
```

### Step 2: Install Python Dependencies
```powershell
cd backend
pip install -r requirements.txt

# Install Playwright for browser skill
pip install playwright
playwright install chromium
```

### Step 3: Install Frontend Dependencies
```powershell
cd ../frontend
npm install
```

### Step 4: Install Electron Dependencies
```powershell
cd ../electron
npm install
```

### Step 5: Configure Environment
```powershell
cd ..
copy .env.example .env
```

Edit `.env` with Notepad:
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3
MEMORY_ENABLED=true
PERMISSION_MODE=ask
```

### Step 6: Start JARVIS

**For development (two terminals):**
```powershell
# Terminal 1 - Backend
cd backend
python main.py

# Terminal 2 - Frontend
cd frontend
npm run dev

# Then open http://localhost:5173 in your browser
```

**Production mode (single window):**
```powershell
cd electron
npm start
```

## Verifying Installation

1. Open JARVIS
2. Check the status indicator (top-right dot):
   - **Green**: Connected to Ollama
   - **Red**: Connection issue
3. Type "Hello" in the chat - JARVIS should respond
4. Test a skill: "List files in C:\Users"
5. Test voice: Press F4 to activate push-to-talk

## Troubleshooting

### "Ollama connection failed"
- Ensure Ollama is running (check system tray for llama icon)
- Run `ollama serve` in terminal
- Check port: `ollama list` should show your models

### "Module not found" errors
- Ensure you installed all dependencies: `pip install -r backend/requirements.txt`
- If using a virtual environment, activate it first

### "Port 8765 already in use"
- Change port in `.env`: `JARVIS_API_PORT=8766`
- Also update `electron/main/main.js` if needed

### Backend crashes on startup
- Check `data/jarvis.log` for error details
- Ensure Python 3.10+ is used: `python --version`
- Try running backend manually: `cd backend && python main.py`

### Skills not loading
- Check that skill folders exist under `/skills/`
- Each skill must have `manifest.json` and `skill.py`
- Check backend logs for skill loading errors

### Voice not working
- For Whisper STT: `pip install faster-whisper`
- For Windows SAPI: No extra install needed
- For Piper TTS: Download a Piper voice model and set `PIPER_MODEL` in `.env`

## Running at Startup

1. Open JARVIS
2. Go to Settings
3. Toggle "Start with Windows"
4. JARVIS will start minimized to system tray on boot

## Updating

```powershell
# Pull latest code
git pull

# Update dependencies
pip install -r backend/requirements.txt --upgrade
cd frontend && npm update
cd ../electron && npm update
```
