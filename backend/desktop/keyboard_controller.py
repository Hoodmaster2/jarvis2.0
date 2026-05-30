"""
Keyboard controller - safe keyboard input with hotkeys and clipboard support.
"""
import asyncio
import logging
import re

logger = logging.getLogger(__name__)

HOTKEY_MAP = {
    "ctrl+c": ["ctrl", "c"],
    "ctrl+v": ["ctrl", "v"],
    "ctrl+x": ["ctrl", "x"],
    "ctrl+z": ["ctrl", "z"],
    "ctrl+s": ["ctrl", "s"],
    "ctrl+a": ["ctrl", "a"],
    "ctrl+f": ["ctrl", "f"],
    "alt+tab": ["alt", "tab"],
    "alt+f4": ["alt", "f4"],
    "win+d": ["win", "d"],
    "win+e": ["win", "e"],
    "win+r": ["win", "r"],
    "enter": ["enter"],
    "escape": ["esc"],
    "tab": ["tab"],
    "delete": ["del"],
    "backspace": ["backspace"],
    "space": ["space"],
}


class KeyboardController:
    def __init__(self):
        pass

    async def type_text(self, text: str, interval: float = 0.05):
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=interval)
            return {"typed": text[:50] + ("..." if len(text) > 50 else "")}
        except Exception as e:
            return await self._powershell_type(text)

    async def _powershell_type(self, text: str):
        import subprocess
        escaped = text.replace("'", "''")
        ps = f"""
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait('{escaped}')
        """
        subprocess.run(["powershell", "-Command", ps], capture_output=True)
        return {"typed": text[:50], "fallback": "powershell"}

    async def hotkey(self, keys: str):
        keys_lower = keys.lower().strip()
        if keys_lower in HOTKEY_MAP:
            key_combo = HOTKEY_MAP[keys_lower]
        else:
            key_combo = re.split(r"\+", keys_lower)

        try:
            import pyautogui
            pyautogui.hotkey(*key_combo)
            return {"hotkey": keys, "keys": key_combo}
        except Exception as e:
            return {"error": str(e)}

    async def press_key(self, key: str, times: int = 1):
        try:
            import pyautogui
            for _ in range(times):
                pyautogui.press(key)
            return {"pressed": key, "times": times}
        except Exception as e:
            return {"error": str(e)}

    async def write_with_modifier(self, modifier: str, text: str):
        try:
            import pyautogui
            pyautogui.keyDown(modifier)
            pyautogui.typewrite(text)
            pyautogui.keyUp(modifier)
            return {"modifier": modifier, "typed": text}
        except Exception as e:
            return {"error": str(e)}
