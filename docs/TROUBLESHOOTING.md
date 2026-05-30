# JARVIS Troubleshooting Guide

## Common Issues

### "Ollama Connection Failed"

**Symptoms**: Red status dot, error messages about Ollama

**Solutions**:
1. Verify Ollama is running:
   ```powershell
   ollama list
   ```
2. Start Ollama if not running:
   ```powershell
   ollama serve
   ```
3. Check OLLAMA_HOST in `.env`:
   - Default: `http://localhost:11434`
   - If using Docker: `http://host.docker.internal:11434`
4. Restart JARVIS backend

### "Model Not Found"

**Symptoms**: Backend logs show "model not found"

**Solutions**:
1. Check available models:
   ```powershell
   ollama list
   ```
2. Pull the required model:
   ```powershell
   ollama pull qwen3
   ```
3. Update OLLAMA_MODEL in `.env` to match an installed model

### Backend Won't Start

**Symptoms**: Electron shows blank screen, Python errors

**Solutions**:
1. Check Python version: `python --version` (needs 3.10+)
2. Install dependencies:
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```
3. Check for port conflicts:
   ```powershell
   netstat -ano | findstr :8765
   ```
4. Change port in `.env`: `JARVIS_API_PORT=8766`
5. Check logs: `type data\jarvis.log`

### Frontend Won't Load (Blank Screen)

**Symptoms**: Electron shows white/blank screen

**Solutions**:
1. Check backend is running (status dot should be green)
2. In dev mode: Ensure Vite is running: `cd frontend && npm run dev`
3. In production: Ensure frontend is built: `cd frontend && npm run build`
4. Open DevTools: In Electron, press F12
5. Check console for errors

### Skills Not Appearing

**Symptoms**: Skills page shows "No skills installed"

**Solutions**:
1. Verify skill folders exist under `jarvis/skills/`
2. Each skill must have both `manifest.json` and `skill.py`
3. Check backend logs for loading errors
4. Click "Reload All" button on Skills page
5. Restart backend

### Voice Input Not Working

**Symptoms**: Voice button does nothing

**Solutions**:
1. Ensure microphone is connected and working
2. For Whisper STT:
   ```powershell
   pip install faster-whisper
   ```
3. For Windows SAPI: Change `STT_ENGINE=windows` in `.env`
4. Check Windows microphone privacy settings:
   - Settings → Privacy & Security → Microphone
   - Allow apps to access your microphone
5. Test with: Press F4 to activate push-to-talk

### Text-to-Speech Not Working

**Symptoms**: JARVIS doesn't speak responses

**Solutions**:
1. For Windows SAPI (default): No install needed
2. For Piper TTS:
   - Download voice model from https://github.com/rhasspy/piper-voices
   - Set `PIPER_MODEL` in `.env` to model path
   - Set `PIPER_PATH` if not in PATH
3. Check system audio output
4. Change `TTS_ENGINE=windows` for fallback

### Electron App Issues

**Symptoms**: Electron crashes, won't open

**Solutions**:
1. Update Electron: `cd electron && npm update electron`
2. Clear Electron cache:
   ```powershell
   rm -r $env:APPDATA/jarvis-electron
   ```
3. Check for Windows updates
4. Run from terminal to see errors:
   ```powershell
   cd electron && npm start
   ```

### Performance Issues

**Symptoms**: Slow responses, high CPU/memory

**Solutions**:
1. Reduce context size: Set `context_size: 4096` in config
2. Use a smaller model: `ollama pull qwen2.5:1.5b`
3. Close other programs using Ollama
4. Disable memory if not needed
5. Update GPU drivers (Ollama uses GPU if available)

### Port Conflicts

**Symptoms**: "Address already in use" errors

**Solutions**:
1. Find what's using port 8765:
   ```powershell
   netstat -ano | findstr :8765
   ```
2. Kill the process or change port in `.env`
3. Common conflicts: Another JARVIS instance, Docker

### "Permission Denied" When Running Commands

**Symptoms**: Shell commands fail with access errors

**Solutions**:
1. Run JARVIS as Administrator for system-level commands
2. Check that PowerShell execution policy allows scripts:
   ```powershell
   Get-ExecutionPolicy
   ```
3. If restricted, run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Memory Database Corrupted

**Symptoms**: Memory operations fail

**Solutions**:
1. Delete `data/memory.db` (backup first if needed)
2. Restart JARVIS (new database will be created)
3. Restore from export if available

## Debug Mode

Enable detailed logging for troubleshooting:

1. Set `LOG_LEVEL=DEBUG` in `.env`
2. Restart JARVIS
3. Check `data/jarvis.log` for detailed information
4. The Logs page in the UI also shows recent entries

## Getting Help

1. Check this troubleshooting guide
2. Review backend logs: `type data\jarvis.log`
3. Check frontend console (F12 in Electron)
4. Look at the Logs page in the UI
5. Search the project issues for similar problems

## Common Error Messages

| Error | Likely Cause | Solution |
|-------|-------------|----------|
| "Ollama connection failed" | Ollama not running | Start Ollama |
| "Model not found" | Wrong model name | Check `ollama list` |
| "Address already in use" | Port conflict | Change port |
| "No module named X" | Missing dependency | `pip install X` |
| "Permission denied" | Access rights | Run as admin |
| "Cannot connect to backend" | Backend not running | Start backend |
| "Skill not found" | Missing skill | Check skills folder |
| "Memory not available" | DB corruption | Delete memory.db |
