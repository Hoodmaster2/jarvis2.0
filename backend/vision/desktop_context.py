import logging
import time
from typing import Dict, List, Optional

from .screen_capture import ScreenCapture
from .ocr_engine import OCREngine
from .window_tracker import WindowTracker

logger = logging.getLogger(__name__)


class DesktopContext:
    def __init__(self, screen_capture: ScreenCapture = None, ocr: OCREngine = None, window_tracker: WindowTracker = None):
        self.screen = screen_capture or ScreenCapture()
        self.ocr = ocr or OCREngine()
        self.window_tracker = window_tracker or WindowTracker()
        self._last_context: Optional[dict] = None

    async def build_context(self, include_screenshot: bool = True, include_ocr: bool = True) -> dict:
        context = {
            "timestamp": time.time(),
            "active_window": self.window_tracker.get_active_window(),
            "open_windows": self.window_tracker.list_windows(limit=10),
        }
        if include_screenshot:
            capture = self.screen.capture_full_screen()
            if capture:
                context["screenshot"] = capture
                if include_ocr:
                    text = self.ocr.extract_text(capture["path"])
                    context["screen_text"] = text[:2000]
                    errors = self._detect_error_text(text)
                    if errors:
                        context["visible_errors"] = errors
        self._last_context = context
        return context

    def _detect_error_text(self, text: str) -> List[str]:
        lines = text.split("\n")
        errors = []
        keywords = ["error", "exception", "failed", "warning", "critical", "stack trace", "traceback"]
        for line in lines:
            line_lower = line.lower().strip()
            if any(kw in line_lower for kw in keywords) and len(line) > 10:
                errors.append(line.strip()[:200])
        return errors[:5]

    def get_last_context(self) -> Optional[dict]:
        return self._last_context

    def interpret_context(self, context: dict = None) -> str:
        ctx = context or self._last_context
        if not ctx:
            return "No desktop context available"
        parts = []
        if ctx.get("active_window"):
            parts.append(f"Active: {ctx['active_window'].get('title', 'unknown')}")
        if ctx.get("visible_errors"):
            parts.append(f"Errors detected: {'; '.join(ctx['visible_errors'][:3])}")
        screen_text = ctx.get("screen_text", "")
        if screen_text:
            text_preview = screen_text[:200].replace("\n", " | ")
            parts.append(f"Screen shows: {text_preview}")
        return " | ".join(parts) if parts else "Desktop visible but no significant content detected"
