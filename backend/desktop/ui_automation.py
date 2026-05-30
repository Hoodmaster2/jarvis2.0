"""
UI automation - interact with UI elements via OCR, coordinates, and app detection.
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class UIAutomation:
    def __init__(self, mouse=None, keyboard=None, window_mgr=None):
        self._mouse = mouse
        self._keyboard = keyboard
        self._window_mgr = window_mgr

    async def click_text(self, text: str, ocr_engine=None):
        """Find text on screen via OCR and click it."""
        if not ocr_engine:
            return {"error": "OCR engine required"}
        try:
            import pyautogui
            locations = list(pyautogui.locateAllOnScreen(text, confidence=0.8))
            if locations:
                x, y, w, h = locations[0]
                center_x = x + w // 2
                center_y = y + h // 2
                if self._mouse:
                    await self._mouse.click(x=center_x, y=center_y)
                return {"clicked": text, "location": (center_x, center_y)}
            return {"error": f"Text '{text}' not found on screen"}
        except ImportError:
            return {"error": "pyautogui image recognition not available"}
        except Exception as e:
            return {"error": str(e)}

    async def find_and_click(self, target: dict) -> dict:
        """Find a UI element by various strategies and click it."""
        strategies = []

        if target.get("text"):
            strategies.append(("text", self.click_text(target["text"])))
        if target.get("image"):
            strategies.append(("image", self._click_image(target["image"])))
        if target.get("coordinates"):
            x, y = target["coordinates"]
            strategies.append(("coords", self._mouse.click(x=x, y=y) if self._mouse else None))

        for name, coro in strategies:
            if coro:
                result = await coro
                if "error" not in result:
                    return {**result, "strategy": name}

        return {"error": "No strategy succeeded"}

    async def _click_image(self, image_path: str):
        try:
            import pyautogui
            location = pyautogui.locateOnScreen(image_path, confidence=0.8)
            if location:
                center = pyautogui.center(location)
                pyautogui.click(center)
                return {"clicked": image_path, "at": (center.x, center.y)}
            return {"error": "Image not found"}
        except Exception as e:
            return {"error": str(e)}

    async def get_screen_text(self) -> str:
        """Extract all text from screen using OCR."""
        try:
            import pyautogui
            import pytesseract
            from PIL import Image
            screenshot = pyautogui.screenshot()
            text = pytesseract.image_to_string(screenshot)
            return text
        except ImportError:
            return "OCR not available (pytesseract required)"
        except Exception as e:
            return f"OCR error: {e}"

    async def detect_app_state(self, app_name: str) -> dict:
        """Detect whether an app is running and its window state."""
        try:
            import psutil
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    if app_name.lower() in proc.info['name'].lower():
                        return {"running": True, "pid": proc.info['pid']}
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return {"running": False}
        except ImportError:
            return {"running": "unknown", "error": "psutil not available"}

    async def launch_app(self, app_path: str, args: str = ""):
        """Launch a desktop application."""
        import subprocess
        try:
            if args:
                subprocess.Popen(f'"{app_path}" {args}', shell=True)
            else:
                subprocess.Popen(f'"{app_path}"', shell=True)
            await asyncio.sleep(1)
            return {"launched": app_path}
        except Exception as e:
            return {"error": str(e)}

    async def wait_for_window(self, title_pattern: str, timeout: int = 10) -> bool:
        """Wait for a window with matching title to appear."""
        import re
        for _ in range(timeout * 2):
            windows = await self._window_mgr.list_windows() if self._window_mgr else []
            for w in windows:
                if re.search(title_pattern, w.get("title", ""), re.IGNORECASE):
                    return True
            await asyncio.sleep(0.5)
        return False
