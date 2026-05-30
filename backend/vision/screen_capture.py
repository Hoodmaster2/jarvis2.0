import logging
import time
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path.home() / ".jarvis" / "screenshots"


class ScreenCapture:
    def __init__(self, save_dir: str = None):
        self._save_dir = Path(save_dir) if save_dir else SCREENSHOT_DIR
        self._save_dir.mkdir(parents=True, exist_ok=True)
        self._capture_enabled = False
        self._last_capture: Optional[dict] = None

    def set_enabled(self, enabled: bool):
        self._capture_enabled = enabled

    def capture_full_screen(self) -> Optional[dict]:
        return self._capture("full")

    def capture_active_window(self) -> Optional[dict]:
        return self._capture("window")

    def capture_region(self, left: int, top: int, width: int, height: int) -> Optional[dict]:
        try:
            import pyautogui
            img = pyautogui.screenshot(region=(left, top, width, height))
            return self._save_image(img, "region")
        except ImportError:
            return self._capture_fallback("region")
        except Exception as e:
            logger.error(f"Region capture failed: {e}")
            return None

    def _capture(self, mode: str) -> Optional[dict]:
        try:
            import pyautogui
            img = pyautogui.screenshot()
            return self._save_image(img, mode)
        except ImportError:
            return self._capture_fallback(mode)
        except Exception as e:
            logger.error(f"Screen capture failed: {e}")
            return None

    def _save_image(self, img, mode: str) -> dict:
        fid = str(uuid4())
        path = self._save_dir / f"{fid}.png"
        img.save(str(path))
        result = {
            "id": fid,
            "path": str(path),
            "mode": mode,
            "width": img.width,
            "height": img.height,
            "timestamp": time.time(),
        }
        self._last_capture = result
        return result

    def _capture_fallback(self, mode: str) -> Optional[dict]:
        try:
            import subprocess
            fid = str(uuid4())
            path = self._save_dir / f"{fid}.png"
            subprocess.run(["powershell", "-Command",
                f"Add-Type -AssemblyName System.Windows.Forms; "
                f"[System.Windows.Forms.Screen]::PrimaryScreen.Bounds | "
                f"ForEach-Object {{ }}"], capture_output=True)
            return {"id": fid, "path": str(path), "mode": mode, "fallback": True, "timestamp": time.time()}
        except Exception as e:
            logger.error(f"Fallback capture failed: {e}")
            return None

    def get_last_capture(self) -> Optional[dict]:
        return self._last_capture

    def get_capture_history(self, limit: int = 20) -> list:
        files = sorted(self._save_dir.glob("*.png"), key=os.path.getmtime, reverse=True)
        history = []
        for f in files[:limit]:
            history.append({
                "id": f.stem,
                "path": str(f),
                "timestamp": os.path.getmtime(f),
                "size": f.stat().st_size,
            })
        return history

    def delete_capture(self, capture_id: str) -> bool:
        path = self._save_dir / f"{capture_id}.png"
        if path.exists():
            path.unlink()
            return True
        return False

    def clear_history(self):
        for f in self._save_dir.glob("*.png"):
            f.unlink()
