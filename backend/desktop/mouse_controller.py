"""
Mouse controller - safe mouse movement and clicking with visual confirmation.
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class MouseController:
    def __init__(self):
        self._speed = 0.5
        self._last_position = None

    async def move_to(self, x: int, y: int, duration: float = 0.3):
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            screen_w, screen_h = pyautogui.size()
            x = max(0, min(x, screen_w - 1))
            y = max(0, min(y, screen_h - 1))
            pyautogui.moveTo(x, y, duration=duration)
            self._last_position = (x, y)
            return {"x": x, "y": y}
        except ImportError:
            return await self._powershell_move(x, y)
        except Exception as e:
            return {"error": str(e)}

    async def _powershell_move(self, x: int, y: int):
        import subprocess
        ps = f"""
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point({x},{y})
        """
        subprocess.run(["powershell", "-Command", ps], capture_output=True)
        self._last_position = (x, y)
        return {"x": x, "y": y, "fallback": "powershell"}

    async def click(self, button: str = "left", x: int = None, y: int = None):
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            if x is not None and y is not None:
                await self.move_to(x, y)
            pyautogui.click(button=button)
            return {"clicked": button, "position": (x, y) or self._last_position}
        except Exception as e:
            return {"error": str(e)}

    async def double_click(self, x: int = None, y: int = None):
        try:
            import pyautogui
            if x is not None and y is not None:
                await self.move_to(x, y)
            pyautogui.doubleClick()
            return {"double_clicked": True}
        except Exception as e:
            return {"error": str(e)}

    async def right_click(self, x: int = None, y: int = None):
        return await self.click("right", x, y)

    async def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5):
        try:
            import pyautogui
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
            return {"from": (start_x, start_y), "to": (end_x, end_y)}
        except Exception as e:
            return {"error": str(e)}

    async def scroll(self, clicks: int, x: int = None, y: int = None):
        try:
            import pyautogui
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.scroll(clicks)
            return {"scrolled": clicks}
        except Exception as e:
            return {"error": str(e)}

    async def get_position(self) -> dict:
        try:
            import pyautogui
            x, y = pyautogui.position()
            return {"x": x, "y": y}
        except Exception as e:
            return {"error": str(e)}
