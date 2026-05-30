"""
Code Editor skill for JARVIS.
Reads, writes, and manages project source code.
"""
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


async def execute(command: str, **kwargs) -> dict:
    commands = {
        "list_files": cmd_list_files,
        "read_file": cmd_read_file,
        "write_file": cmd_write_file,
        "run_tests": cmd_run_tests,
        "run_command": cmd_run_command,
        "analyze": cmd_analyze,
    }
    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return await handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


async def cmd_list_files(path: str) -> dict:
    """List all files in a project, respecting .gitignore."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Path not found: {path}"}

    files = []
    for f in sorted(p.rglob("*")):
        if f.is_file():
            try:
                rel = f.relative_to(p)
                files.append({
                    "name": f.name,
                    "path": str(f),
                    "relative": str(rel),
                    "size": f.stat().st_size,
                })
            except ValueError:
                continue

    return {"files": files, "count": len(files), "project": path}


async def cmd_read_file(path: str) -> dict:
    """Read a source file."""
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        return {"error": f"File not found: {path}"}

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"content": content, "path": str(p), "size": len(content), "language": p.suffix}
    except Exception as e:
        return {"error": str(e)}


async def cmd_write_file(path: str, content: str) -> dict:
    """Write a source file."""
    p = Path(path).resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "written", "path": str(p), "size": len(content)}
    except Exception as e:
        return {"error": str(e)}


async def cmd_run_tests(path: str, command: str = None) -> dict:
    """Run tests in the project."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Path not found: {path}"}

    # Auto-detect test framework
    if not command:
        if (p / "package.json").exists():
            command = "npm test"
        elif (p / "pytest.ini").exists() or (p / "setup.py").exists():
            command = "pytest"
        elif (p / "Cargo.toml").exists():
            command = "cargo test"
        else:
            command = "python -m pytest"

    try:
        proc = await asyncio.create_subprocess_exec(
            "cmd", "/c", command,
            cwd=str(p),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "stdout": stdout.decode("utf-8", errors="replace")[:10000],
            "stderr": stderr.decode("utf-8", errors="replace")[:5000],
            "returncode": proc.returncode,
            "command": command,
        }
    except Exception as e:
        return {"error": str(e)}


async def cmd_run_command(path: str, command: str) -> dict:
    """Run a development command."""
    p = Path(path).resolve()

    try:
        proc = await asyncio.create_subprocess_exec(
            "cmd", "/c", command,
            cwd=str(p),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "stdout": stdout.decode("utf-8", errors="replace")[:10000],
            "stderr": stderr.decode("utf-8", errors="replace")[:5000],
            "returncode": proc.returncode,
        }
    except Exception as e:
        return {"error": str(e)}


async def cmd_analyze(path: str) -> dict:
    """Analyze project structure."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Path not found: {path}"}

    analysis = {
        "name": p.name,
        "files": 0,
        "dirs": 0,
        "total_size": 0,
        "languages": {},
        "has_git": (p / ".git").exists(),
        "has_package_json": (p / "package.json").exists(),
        "has_requirements": (p / "requirements.txt").exists(),
        "has_setup_py": (p / "setup.py").exists(),
        "has_cargo": (p / "Cargo.toml").exists(),
        "top_files": [],
    }

    for f in p.rglob("*"):
        try:
            if f.is_file():
                analysis["files"] += 1
                analysis["total_size"] += f.stat().st_size
                ext = f.suffix.lower()
                analysis["languages"][ext] = analysis["languages"].get(ext, 0) + 1
            elif f.is_dir():
                analysis["dirs"] += 1
        except (PermissionError, OSError):
            continue

    # Top 10 largest files
    files_sorted = sorted(
        [f for f in p.rglob("*") if f.is_file()],
        key=lambda x: x.stat().st_size,
        reverse=True,
    )[:10]
    analysis["top_files"] = [
        {"name": str(f.relative_to(p)), "size": f.stat().st_size}
        for f in files_sorted
    ]

    return analysis
