"""
PowerShell Runner skill for JARVIS.
Executes PowerShell commands with proper permission checks.
Requires HIGH permission level.
"""
import asyncio
import logging
import subprocess

logger = logging.getLogger(__name__)

BLOCKED_COMMANDS = [
    "format",
    "rm -rf",
    "del /f /s",
    "rd /s /q",
    "shutdown /r",
    "shutdown /s",
    "net user /delete",
    "reg delete",
]


async def execute(command: str, **kwargs) -> dict:
    commands = {
        "run": cmd_run,
        "run_script": cmd_run_script,
    }
    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return await handler(**kwargs)
    except Exception as e:
        logger.error(f"PowerShell error: {e}")
        return {"error": str(e)}


def _is_blocked(cmd: str) -> bool:
    cmd_lower = cmd.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return True
    return False


async def cmd_run(command: str, description: str = "") -> dict:
    """Run a PowerShell command."""
    if _is_blocked(command):
        return {
            "error": "Command blocked for safety",
            "command": command,
            "blocked": True,
        }

    logger.info(f"Executing PowerShell: {command[:200]}")

    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-Command", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        return {
            "status": "completed" if proc.returncode == 0 else "error",
            "stdout": stdout.decode("utf-8", errors="replace")[:10000],
            "stderr": stderr.decode("utf-8", errors="replace")[:5000],
            "returncode": proc.returncode,
        }
    except Exception as e:
        return {"error": str(e)}


async def cmd_run_script(path: str) -> dict:
    """Run a PowerShell script file."""
    import os
    if not os.path.exists(path):
        return {"error": f"Script not found: {path}"}

    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        return {
            "status": "completed" if proc.returncode == 0 else "error",
            "stdout": stdout.decode("utf-8", errors="replace")[:10000],
            "stderr": stderr.decode("utf-8", errors="replace")[:5000],
            "returncode": proc.returncode,
        }
    except Exception as e:
        return {"error": str(e)}
