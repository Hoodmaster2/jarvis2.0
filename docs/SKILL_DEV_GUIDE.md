# JARVIS Skill Development Guide

## Overview

Skills extend JARVIS's capabilities. Each skill is a directory under `/skills/` with a `manifest.json` file and an implementation file (`skill.py` or `skill.js`).

## Skill Structure

```
skills/<skill_name>/
├── manifest.json     # Required: metadata, permissions, commands
├── skill.py          # Required: Python implementation
├── skill.js          # Alternative: Node.js implementation
├── install.ps1       # Optional: install script
└── uninstall.ps1     # Optional: uninstall script
```

## Manifest Format

```json
{
  "name": "my_skill",
  "version": "1.0.0",
  "description": "What this skill does",
  "author": "Your Name",
  "permissions": ["safe"],
  "commands": [
    {
      "name": "hello",
      "description": "Say hello",
      "parameters": {
        "name": {
          "type": "string",
          "description": "Name to greet"
        }
      },
      "required": ["name"]
    }
  ]
}
```

### Fields

| Field | Description |
|-------|-------------|
| `name` | Unique skill identifier (lowercase, underscores) |
| `version` | Semantic version |
| `description` | Brief description shown in UI |
| `author` | Creator name |
| `permissions` | Array of required permission levels |
| `commands` | Array of command definitions |

### Permissions

| Level | Description |
|-------|-------------|
| `safe` | Read-only operations |
| `medium` | Create/edit files |
| `high` | Shell commands, system changes |
| `critical` | Delete, network, dangerous |

### Command Parameters

Each parameter supports:
- `type`: `string`, `number`, `boolean`, `array`, `object`
- `description`: Human-readable explanation
- `enum`: Array of allowed values (optional)

## Python Skill Implementation

Your `skill.py` must expose an `async def execute(command, **kwargs)` function:

```python
"""
My Skill - Example skill for JARVIS.
"""
import logging

logger = logging.getLogger(__name__)


async def execute(command: str, **kwargs) -> dict:
    """Main entry point. Called by JARVIS."""
    commands = {
        "hello": cmd_hello,
    }
    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return await handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


async def cmd_hello(name: str = "World") -> dict:
    """Say hello to someone."""
    return {
        "message": f"Hello, {name}!",
        "greeted": name,
    }
```

### Rules

1. Always return a `dict`
2. Return `{"error": "..."}` on failure
3. Use `logging` for debugging
4. Keep functions focused (one per command)
5. Validate parameters inside the command function
6. Don't block - use `async/await` for I/O

## Node.js Skill Implementation

Alternative implementation using JavaScript/Node.js:

```javascript
// skill.js
module.exports = {
  async execute(command, kwargs) {
    const commands = {
      hello: async (name = 'World') => ({
        message: `Hello, ${name}!`,
        greeted: name,
      }),
    };
    const handler = commands[command];
    if (!handler) return { error: `Unknown command: ${command}` };
    try {
      return await handler(...kwargs);
    } catch (err) {
      return { error: err.message };
    }
  },
};
```

## Security Best Practices

1. **Never** hardcode API keys or secrets in skills
2. Use appropriate permission levels
3. Validate all user-supplied paths (prevent path traversal)
4. Limit file operations to safe directories
5. Ask for confirmation via HIGH/CRITICAL permission levels
6. Log all operations for audit

## Testing Your Skill

1. Place your skill folder in `/skills/`
2. Restart JARVIS backend (or click "Reload All" in Skills page)
3. The skill should appear in the Skills UI
4. Test via Chat: "Use my_skill to hello name=Alice"
5. Check logs in the Logs page

## Example: Complete Skill

### manifest.json
```json
{
  "name": "greeter",
  "version": "1.0.0",
  "description": "Greets users in different languages",
  "author": "JARVIS",
  "permissions": ["safe"],
  "commands": [
    {
      "name": "greet",
      "description": "Greet someone",
      "parameters": {
        "name": { "type": "string", "description": "Person to greet" },
        "language": { "type": "string", "description": "en, es, fr, de", "enum": ["en", "es", "fr", "de"] }
      },
      "required": ["name"]
    },
    {
      "name": "languages",
      "description": "List supported languages",
      "parameters": {}
    }
  ]
}
```

### skill.py
```python
import logging
logger = logging.getLogger(__name__)

GREETINGS = {
    "en": "Hello",
    "es": "Hola",
    "fr": "Bonjour",
    "de": "Hallo",
}

async def execute(command, **kwargs):
    handlers = {
        "greet": cmd_greet,
        "languages": cmd_languages,
    }
    handler = handlers.get(command)
    if not handler:
        return {"error": f"Unknown: {command}"}
    return await handler(**kwargs)

async def cmd_greet(name: str, language: str = "en"):
    greeting = GREETINGS.get(language, GREETINGS["en"])
    return {"message": f"{greeting}, {name}!", "language": language}

async def cmd_languages():
    return {"languages": list(GREETINGS.keys())}
```

## Installing Skills

### Via UI
1. Go to Skills page
2. Enter path to skill directory
3. Click "Install"

### Via API
```powershell
curl -X POST http://127.0.0.1:8765/api/skills/install ^
  -H "Content-Type: application/json" ^
  -d '{"source": "C:\\path\\to\\skill_folder"}'
```

### Manually
Copy the skill folder to `/skills/` and restart the backend.
