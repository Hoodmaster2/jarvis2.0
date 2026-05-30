"""
File Manager skill for JARVIS.
Handles listing, reading, creating, editing, and searching files.
"""
import os
import glob as glob_mod
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ALLOWED_ROOTS = [
    os.environ.get("USERPROFILE", "C:\\Users"),
    os.environ.get("LOCALAPPDATA", ""),
    "C:\\",
    "D:\\",
]


async def execute(command: str, **kwargs) -> dict:
    """Execute a file manager command."""
    commands = {
        "list": cmd_list,
        "read": cmd_read,
        "create": cmd_create,
        "edit": cmd_edit,
        "search": cmd_search,
        "move": cmd_move,
        "delete": cmd_delete,
    }

    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}

    try:
        return await handler(**kwargs)
    except Exception as e:
        logger.error(f"File manager error: {e}")
        return {"error": str(e)}


async def cmd_list(path: str = ".") -> dict:
    """List directory contents."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Path not found: {path}"}
    if not p.is_dir():
        return {"error": f"Not a directory: {path}"}

    files = []
    for entry in sorted(p.iterdir()):
        try:
            stat = entry.stat()
            files.append({
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
                "size": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
        except PermissionError:
            files.append({"name": entry.name, "path": str(entry), "is_dir": True, "size": 0, "modified": 0})

    return {"files": files, "path": str(p)}


async def cmd_read(path: str) -> dict:
    """Read file contents."""
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        return {"error": f"File not found: {path}"}

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"content": content, "path": str(p), "size": len(content)}
    except Exception as e:
        return {"error": f"Cannot read file: {e}"}


async def cmd_create(path: str, content: str = "") -> dict:
    """Create a new file."""
    p = Path(path).resolve()
    if p.exists():
        return {"error": f"File already exists: {path}"}

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Created file: {p}")
        return {"status": "created", "path": str(p)}
    except Exception as e:
        return {"error": f"Cannot create file: {e}"}


async def cmd_edit(path: str, content: str, mode: str = "replace") -> dict:
    """Edit an existing file."""
    p = Path(path).resolve()
    if not p.exists() or not p.is_file():
        return {"error": f"File not found: {path}"}

    try:
        if mode == "append":
            with open(p, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
        logger.info(f"Edited file: {p} (mode={mode})")
        return {"status": "edited", "path": str(p), "mode": mode}
    except Exception as e:
        return {"error": f"Cannot edit file: {e}"}


async def cmd_search(pattern: str, path: str = ".") -> dict:
    """Search for files by glob pattern."""
    p = Path(path).resolve()
    try:
        matches = [str(f) for f in p.rglob(pattern)]
        return {"results": matches, "count": len(matches), "pattern": pattern}
    except Exception as e:
        return {"error": f"Search error: {e}"}


async def cmd_move(source: str, destination: str) -> dict:
    """Move or rename a file."""
    src = Path(source).resolve()
    dst = Path(destination).resolve()

    if not src.exists():
        return {"error": f"Source not found: {source}"}

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        logger.info(f"Moved: {src} -> {dst}")
        return {"status": "moved", "source": str(src), "destination": str(dst)}
    except Exception as e:
        return {"error": f"Cannot move file: {e}"}


async def cmd_delete(path: str) -> dict:
    """Delete a file."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}

    try:
        if p.is_dir():
            import shutil
            shutil.rmtree(p)
        else:
            p.unlink()
        logger.info(f"Deleted: {p}")
        return {"status": "deleted", "path": str(p)}
    except Exception as e:
        return {"error": f"Cannot delete: {e}"}
