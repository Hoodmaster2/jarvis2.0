import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class UIDetector:
    def detect_elements(self, image_path: str) -> List[dict]:
        elements = []
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(image_path)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                if text and int(data["conf"][i]) > 40:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    elements.append({
                        "type": self._classify_element(text, x, y, w, h),
                        "text": text,
                        "bounds": {"x": x, "y": y, "width": w, "height": h},
                        "confidence": int(data["conf"][i]),
                    })
        except Exception as e:
            logger.error(f"UI detection failed: {e}")
        return elements

    def _classify_element(self, text: str, x: int, y: int, w: int, h: int) -> str:
        if h > 30 and w > 100:
            return "button" if any(kw in text.lower() for kw in ["ok", "cancel", "submit", "save", "delete", "yes", "no", "apply"]) else "panel"
        elif w > 200:
            return "text_field" if h > 20 else "label"
        elif w < 30 and h < 30:
            return "icon"
        return "text"

    def detect_buttons(self, image_path: str) -> List[dict]:
        return [e for e in self.detect_elements(image_path) if e["type"] == "button"]

    def detect_text_fields(self, image_path: str) -> List[dict]:
        return [e for e in self.detect_elements(image_path) if e["type"] == "text_field"]

    def detect_errors(self, image_path: str) -> List[dict]:
        elements = self.detect_elements(image_path)
        return [e for e in elements if any(kw in e["text"].lower() for kw in
                ["error", "failed", "exception", "warning", "critical", "missing", "denied"])]
