"""
App state detector - detect running applications, system dialogs, and desktop state.
"""
import asyncio
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class AppStateDetector:
    def __init__(self, window_mgr=None):
        self._window_mgr = window_mgr
        self._mode = "safe"

    async def get_desktop_state(self) -> dict:
        windows = await self._window_mgr.list_windows() if self._window_mgr else []
        active = await self._window_mgr.get_active_window() if self._window_mgr else {}
        return {
            "active_window": active,
            "open_windows": windows,
            "window_count": len(windows),
            "mode": self._mode,
        }

    async def get_running_apps(self) -> list[dict]:
        try:
            import psutil
            apps = []
            seen = set()
            for proc in psutil.process_iter(['name', 'pid', 'cpu_percent', 'memory_percent']):
                try:
                    name = proc.info['name']
                    if name and name.lower() not in seen and name.lower() not in (
                        'svchost.exe', 'system', 'registry', 'idle',
                    ):
                        seen.add(name.lower())
                        apps.append({
                            "name": name,
                            "pid": proc.info['pid'],
                            "cpu": proc.info['cpu_percent'] or 0,
                            "memory": proc.info['memory_percent'] or 0,
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            apps.sort(key=lambda a: -a["memory"])
            return apps[:50]
        except ImportError:
            return [{"name": "psutil not available"}]

    async def detect_dialogs(self) -> list[dict]:
        """Detect system dialogs like error messages, confirmations."""
        if not self._window_mgr:
            return []
        windows = await self._window_mgr.list_windows()
        dialog_keywords = ["error", "warning", "confirm", "alert", "message",
                          "dialog", "notification", "failed", "exception"]
        dialogs = []
        for w in windows:
            title = w.get("title", "").lower()
            for kw in dialog_keywords:
                if kw in title:
                    dialogs.append({
                        "title": w.get("title"),
                        "matched_keyword": kw,
                        "type": "dialog",
                    })
                    break
        return dialogs

    async def is_ide_active(self) -> bool:
        active = await self._window_mgr.get_active_window() if self._window_mgr else {}
        title = active.get("title", "").lower()
        ide_keywords = ["vs code", "visual studio", "pycharm", "intellij", "sublime",
                       "atom", "vim", "notepad++", "cursor", "windsurf"]
        return any(k in title for k in ide_keywords)

    async def is_browser_active(self) -> bool:
        active = await self._window_mgr.get_active_window() if self._window_mgr else {}
        title = active.get("title", "").lower()
        browser_keywords = ["chrome", "firefox", "edge", "brave", "opera", "browser"]
        return any(k in title for k in browser_keywords)

    async def get_focused_app_type(self) -> str:
        if await self.is_ide_active():
            return "ide"
        if await self.is_browser_active():
            return "browser"
        active = await self._window_mgr.get_active_window() if self._window_mgr else {}
        title = active.get("title", "").lower()
        if "terminal" in title or "cmd" in title or "powershell" in title:
            return "terminal"
        if "explorer" in title or "file" in title:
            return "file_manager"
        return "other"

    def set_mode(self, mode: str):
        if mode in ("safe", "developer", "autonomous"):
            self._mode = mode

    def get_mode(self) -> str:
        return self._mode
