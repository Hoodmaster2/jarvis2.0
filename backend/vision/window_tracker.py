import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class WindowTracker:
    def __init__(self):
        self._windows_cache: list = []
        self._last_refresh = 0.0

    def get_active_window(self) -> Optional[dict]:
        try:
            import pygetwindow as gw
            active = gw.getActiveWindow()
            if active:
                return {
                    "title": active.title,
                    "left": active.left,
                    "top": active.top,
                    "width": active.width,
                    "height": active.height,
                }
        except ImportError:
            return self._fallback_active_window()
        except Exception as e:
            logger.warning(f"get_active_window failed: {e}")
        return None

    def list_windows(self, limit: int = 20) -> List[dict]:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle("")
            result = []
            for w in windows:
                if w.title.strip():
                    result.append({
                        "title": w.title.strip(),
                        "visible": w.visible,
                        "left": w.left,
                        "top": w.top,
                        "width": w.width,
                        "height": w.height,
                    })
                    if len(result) >= limit:
                        break
            return result
        except ImportError:
            return self._fallback_list_windows(limit)
        except Exception as e:
            logger.warning(f"list_windows failed: {e}")
            return []

    def _fallback_active_window(self) -> Optional[dict]:
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command",
                 "[System.Windows.Forms.Cursor]::Position | ForEach-Object { (Get-Process | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1).MainWindowTitle }"],
                capture_output=True, text=True, timeout=5
            )
            title = result.stdout.strip()
            if title:
                return {"title": title}
        except Exception:
            pass
        return None

    def _fallback_list_windows(self, limit: int) -> List[dict]:
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | Select-Object -First 20 MainWindowTitle"],
                capture_output=True, text=True, timeout=5
            )
            lines = [l.strip() for l in result.stdout.split("\n") if l.strip() and "MainWindowTitle" not in l]
            return [{"title": l} for l in lines[:limit]]
        except Exception:
            return []
