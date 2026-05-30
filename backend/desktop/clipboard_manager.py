"""
Clipboard manager - read/write clipboard with async support.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


class ClipboardManager:
    def __init__(self):
        pass

    async def read_text(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            return self._powershell_read()
        except Exception as e:
            return f"Clipboard read error: {e}"

    def _powershell_read(self):
        import subprocess
        try:
            ps = "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::GetText()"
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"

    async def write_text(self, text: str):
        try:
            import pyperclip
            pyperclip.copy(text)
            return {"written": len(text), "preview": text[:50]}
        except ImportError:
            return self._powershell_write(text)
        except Exception as e:
            return {"error": str(e)}

    def _powershell_write(self, text: str):
        import subprocess
        try:
            escaped = text.replace("'", "''")
            ps = f"""
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.Clipboard]::SetText('{escaped}')
            """
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=5
            )
            return {"written": len(text), "preview": text[:50]}
        except Exception as e:
            return {"error": str(e)}

    async def clear(self):
        try:
            import pyperclip
            pyperclip.copy("")
            return {"cleared": True}
        except Exception:
            return self._powershell_clear()

    def _powershell_clear(self):
        import subprocess
        try:
            ps = "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::Clear()"
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=5)
            return {"cleared": True}
        except Exception as e:
            return {"error": str(e)}

    async def has_text(self) -> bool:
        text = await self.read_text()
        return bool(text.strip())
