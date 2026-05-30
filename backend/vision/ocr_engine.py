import logging
import tempfile
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class OCREngine:
    def __init__(self, tesseract_cmd: str = None):
        self._tesseract_cmd = tesseract_cmd
        self._available = self._check_available()

    def _check_available(self) -> bool:
        try:
            import pytesseract
            if self._tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            logger.warning("Tesseract OCR not available")
            return False

    def extract_text(self, image_path: str) -> str:
        if not self._available:
            return "OCR not available - install tesseract and pytesseract"
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    def extract_text_with_boxes(self, image_path: str) -> List[dict]:
        if not self._available:
            return []
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(image_path)
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            results = []
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                if text and int(data["conf"][i]) > 30:
                    results.append({
                        "text": text,
                        "confidence": int(data["conf"][i]),
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i],
                    })
            return results
        except Exception as e:
            logger.error(f"OCR box extraction failed: {e}")
            return []

    def is_available(self) -> bool:
        return self._available
