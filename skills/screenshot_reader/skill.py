"""
Screenshot Reader skill for JARVIS.
Captures and analyzes screen content.
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


async def execute(command: str, **kwargs) -> dict:
    commands = {
        "capture": cmd_capture,
        "capture_region": cmd_capture_region,
    }
    handler = commands.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}
    try:
        return await handler(**kwargs)
    except Exception as e:
        return {"error": str(e)}


async def cmd_capture(path: str = None) -> dict:
    """Take a full screen screenshot."""
    try:
        from PIL import ImageGrab
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = str(Path(tempfile.gettempdir()) / f"jarvis_screenshot_{timestamp}.png")

        img = ImageGrab.grab()
        img.save(path)
        return {"status": "captured", "path": path, "size": img.size}
    except ImportError:
        return {"error": "PIL not installed. Run: pip install pillow"}
    except Exception as e:
        return {"error": str(e)}


async def cmd_capture_region(left: int, top: int, width: int, height: int) -> dict:
    """Capture a region of the screen."""
    try:
        from PIL import ImageGrab
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(Path(tempfile.gettempdir()) / f"jarvis_region_{timestamp}.png")

        img = ImageGrab.grab(bbox=(left, top, left + width, top + height))
        img.save(path)
        return {"status": "captured", "path": path, "region": {"left": left, "top": top, "width": width, "height": height}}
    except ImportError:
        return {"error": "PIL not installed"}
    except Exception as e:
        return {"error": str(e)}
