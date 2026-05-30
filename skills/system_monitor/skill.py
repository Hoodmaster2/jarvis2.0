"""
System Monitor skill for JARVIS.
Tracks CPU, RAM, disk, and process metrics.
"""
import asyncio
import json
import logging
import subprocess

logger = logging.getLogger(__name__)


async def execute(command: str, **kwargs) -> dict:
    commands = {
        "get_cpu": cmd_get_cpu,
        "get_memory": cmd_get_memory,
        "get_disk": cmd_get_disk,
        "get_all": cmd_get_all,
    }
    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return await handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


async def _run_powershell(script: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "powershell", "-NoProfile", "-Command", script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode("utf-8", errors="replace").strip()


async def cmd_get_cpu() -> dict:
    out = await _run_powershell(
        "Get-CimInstance Win32_Processor | Select-Object Name, LoadPercentage, NumberOfCores, MaxClockSpeed | ConvertTo-Json"
    )
    try:
        data = json.loads(out)
        return {"cpu": data}
    except json.JSONDecodeError:
        return {"cpu": {"raw": out}}


async def cmd_get_memory() -> dict:
    out = await _run_powershell(
        "Get-CimInstance Win32_OperatingSystem | Select-Object @{Name='TotalGB';Expression={[math]::Round($_.TotalVisibleMemorySize/1MB,1)}}, @{Name='FreeGB';Expression={[math]::Round($_.FreePhysicalMemory/1MB,1)}}, @{Name='UsedGB';Expression={[math]::Round(($_.TotalVisibleMemorySize-$_.FreePhysicalMemory)/1MB,1)}} | ConvertTo-Json"
    )
    try:
        data = json.loads(out)
        return {"memory": data}
    except json.JSONDecodeError:
        return {"memory": {"raw": out}}


async def cmd_get_disk() -> dict:
    out = await _run_powershell(
        "Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID, @{Name='SizeGB';Expression={[math]::Round($_.Size/1GB,1)}}, @{Name='FreeGB';Expression={[math]::Round($_.FreeSpace/1GB,1)}} | ConvertTo-Json"
    )
    try:
        data = json.loads(out)
        return {"disk": data}
    except json.JSONDecodeError:
        return {"disk": {"raw": out}}


async def cmd_get_all() -> dict:
    cpu = await cmd_get_cpu()
    mem = await cmd_get_memory()
    disk = await cmd_get_disk()
    return {"cpu": cpu.get("cpu"), "memory": mem.get("memory"), "disk": disk.get("disk")}
