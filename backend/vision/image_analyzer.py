import base64
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    def __init__(self, llm_analyze_fn: Callable = None):
        self.llm_analyze_fn = llm_analyze_fn

    def set_analyze_fn(self, fn: Callable):
        self.llm_analyze_fn = fn

    async def analyze_image(self, image_path: str, prompt: str = "Describe this image in detail.") -> str:
        if self.llm_analyze_fn:
            try:
                result = await self.llm_analyze_fn(image_path, prompt)
                return result
            except Exception as e:
                logger.error(f"LLM image analysis failed: {e}")
        return self._basic_analysis(image_path)

    def _basic_analysis(self, image_path: str) -> str:
        try:
            from PIL import Image
            img = Image.open(image_path)
            info = {
                "format": img.format,
                "size": img.size,
                "mode": img.mode,
                "width": img.width,
                "height": img.height,
            }
            return f"Image: {info['width']}x{info['height']} {info['format']} ({info['mode']})"
        except Exception as e:
            return f"Could not analyze image: {e}"

    def encode_image(self, image_path: str) -> Optional[str]:
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return None
