"""
Window manager - detect, list, switch, and control application windows.
"""
import asyncio
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class WindowManager:
    def __init__(self):
        pass

    async def list_windows(self) -> list[dict]:
        try:
            return await self._pygetwindow_list()
        except ImportError:
            return self._powershell_list()

    async def _pygetwindow_list(self):
        import pygetwindow as gw
        windows = gw.getAllWindows()
        result = []
        for w in windows:
            if w.title.strip():
                result.append({
                    "title": w.title,
                    "left": w.left, "top": w.top,
                    "width": w.width, "height": w.height,
                    "active": w.isActive,
                    "minimized": w.isMinimized,
                    "maximized": w.isMaximized,
                })
        return result

    def _powershell_list(self):
        import subprocess
        try:
            ps = """
            Add-Type @"
                using System;
                using System.Runtime.InteropServices;
                using System.Text;
                using System.Diagnostics;
                public class WinAPI {
                    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
                    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
                    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
                    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
                    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
                    public static string GetWindowTitle(IntPtr hWnd) {
                        StringBuilder sb = new StringBuilder(256);
                        GetWindowText(hWnd, sb, 256);
                        return sb.ToString();
                    }
                }
"@
                $titles = @()
                $proc = [WinAPI]::EnumWindows({ param($hWnd, $lParam)
                    if ([WinAPI]::IsWindowVisible($hWnd)) {
                        $title = [WinAPI]::GetWindowTitle($hWnd)
                        if ($title) { $titles += $title }
                    }
                    return $true
                }, 0)
                $titles | ConvertTo-Json
            """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=10
            )
            titles = []
            import json
            try:
                titles = json.loads(result.stdout) if result.stdout.strip() else []
            except json.JSONDecodeError:
                titles = result.stdout.strip().split("\n") if result.stdout.strip() else []
            if isinstance(titles, str):
                titles = [titles]
            return [{"title": t} for t in titles if t.strip()]
        except Exception as e:
            return [{"title": f"Error: {e}"}]

    async def get_active_window(self) -> Optional[dict]:
        try:
            import pygetwindow as gw
            w = gw.getActiveWindow()
            if w and w.title:
                return {
                    "title": w.title,
                    "left": w.left, "top": w.top,
                    "width": w.width, "height": w.height,
                }
        except ImportError:
            pass
        except Exception:
            pass

        try:
            import pyautogui
            return {"title": pyautogui.getActiveWindowTitle() or "Unknown"}
        except Exception:
            pass

        return {"title": "Unknown"}

    async def focus_window(self, title_match: str) -> bool:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_match)
            if windows:
                w = windows[0]
                w.activate()
                await asyncio.sleep(0.3)
                return True
        except ImportError:
            pass
        except Exception:
            pass

        try:
            import subprocess
            ps = f"""
            Add-Type -AssemblyName Microsoft.VisualBasic
            [Microsoft.VisualBasic.Interaction]::AppActivate('{title_match}')
            """
            subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=5)
            return True
        except Exception:
            pass

        return False

    async def minimize_window(self, title_match: str) -> bool:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_match)
            if windows:
                windows[0].minimize()
                return True
        except Exception:
            pass
        return False

    async def maximize_window(self, title_match: str) -> bool:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_match)
            if windows:
                windows[0].maximize()
                return True
        except Exception:
            pass
        return False

    async def close_window(self, title_match: str) -> bool:
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(title_match)
            if windows:
                windows[0].close()
                return True
        except Exception:
            pass
        return False
