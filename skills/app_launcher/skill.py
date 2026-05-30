"""
App Launcher skill for JARVIS.
Launch applications and manage processes on Windows.
"""
import asyncio
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


async def execute(command: str, **kwargs) -> dict:
    commands = {
        "launch": cmd_launch,
        "list_running": cmd_list_running,
        "find_app": cmd_find_app,
    }
    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return await handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


async def cmd_launch(app: str) -> dict:
    """Launch an application."""
    try:
        if os.path.exists(app):
            proc = await asyncio.create_subprocess_exec(app, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        else:
            proc = await asyncio.create_subprocess_exec(
                "cmd", "/c", "start", "", app,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        await proc.wait()
        return {"status": "launched", "app": app}
    except Exception as e:
        return {"error": str(e)}


async def cmd_list_running() -> dict:
    """List running processes."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-Command", "Get-Process | Select-Object Name, Id, CPU, WorkingSet | ConvertTo-Json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        import json
        processes = json.loads(stdout)
        if isinstance(processes, dict):
            processes = [processes]
        return {"processes": processes[:100]}
    except Exception as e:
        return {"error": str(e)}


async def cmd_find_app(name: str) -> dict:
    """Find installed applications by name."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-Command",
            f"Get-StartApps | Where-Object {{ $_.Name -like '*{name}*' }} | Select-Object Name, AppId | ConvertTo-Json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        import json
        results = json.loads(stdout) if stdout.strip() else []
        if isinstance(results, dict):
            results = [results]
        return {"results": results, "query": name}
    except Exception as e:
        return {"error": str(e)}
