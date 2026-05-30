# JARVIS Security Model

## Overview

JARVIS is designed with a **zero-trust security model**. Every action is classified by risk level, and dangerous operations require explicit user confirmation.

Your safety is the top priority. JARVIS will **never** perform destructive actions without asking first.

## Permission Levels

| Level | Examples | Default Behavior |
|-------|----------|------------------|
| **Safe** | Reading files, searching, chat, getting system info | Auto-allowed |
| **Medium** | Creating/editing files, clipboard read/write | Auto-allowed (configurable) |
| **High** | Shell commands, installing software, changing system settings | **Asks for confirmation** |
| **Critical** | Deleting files, formatting, sending messages, payments | **Asks for confirmation** |

## Permission Mode

Configured via `PERMISSION_MODE` in `.env` or `security.mode` in config:

| Mode | Behavior |
|------|----------|
| `ask` (default) | Confirm HIGH and CRITICAL actions |
| `auto` | Auto-approve all (not recommended) |
| `strict` | Confirm ALL actions |

## Risk Detection

JARVIS automatically classifies actions by scanning for risk keywords:

**Critical keywords**: `delete`, `remove`, `uninstall`, `kill`, `format`, `rm -rf`, `del /f`, `reg delete`, `net user /delete`

**High keywords**: `install`, `shutdown`, `restart`, `sudo`, `admin`, `reg add`, `set-executionpolicy`

## Safe Guards

### File Operations
- File deletion uses CRITICAL level (always asks)
- File creation/editing uses MEDIUM level
- Path traversal attempts are blocked
- Operations are logged

### Shell Commands
- PowerShell execution uses HIGH level (asks permission)
- Certain commands are blocked entirely (`format`, `shutdown`, destructive `reg` operations)
- Command output is limited to 10KB
- Timeout enforced (30 seconds)

### Browser Automation
- Navigation: SAFE
- Form filling: SAFE
- Downloads: MEDIUM (asks before saving)
- File access through browser: CRITICAL

### System Settings
- Reading settings: SAFE
- Changing settings: HIGH (asks permission)
- Registry modifications: CRITICAL

## User Confirmation Flow

When JARVIS needs to perform a HIGH or CRITICAL action:

1. JARVIS displays a description of the action
2. Shows the risk level
3. Asks "Approve?" with Yes/No buttons
4. User reviews and responds
5. Action proceeds only if approved
6. All decisions are logged

## Data Privacy

- **All processing is local** - No data sent to external servers
- **No telemetry** - JARVIS does not phone home
- **No analytics** - No tracking or usage data collection
- **Memory is optional** - Can be disabled in settings
- **Export/delete** - Full control over stored data

## API Keys and Secrets

- API keys are stored in `.env` (not in code)
- The `.env` file is in `.gitignore` (never committed)
- Credentials are loaded at runtime only
- No secrets are exposed in logs

## Recommendations

1. **Always use `ask` mode** for best security
2. **Review pending permissions** regularly in the Status panel
3. **Export your memory** periodically as backup
4. **Disable unused skills** in the Skills page
5. **Keep Ollama updated** for latest model security
6. **Review logs** for any unexpected activity

## Reporting Issues

If you find a security issue, please report it immediately via the project's issue tracker. Do not post security issues publicly.
