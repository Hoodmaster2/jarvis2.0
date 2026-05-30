"""
Ollama API client with streaming, tool calling, and embedding support.
Compatible with OpenAI API format.
"""
import json
import logging
import httpx
from typing import AsyncGenerator, Optional, Callable

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama local API with function/tool calling support."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen3"):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = 120.0
        self._http = httpx.AsyncClient(timeout=self.timeout)

    async def list_models(self) -> list:
        """Fetch available models from Ollama."""
        try:
            resp = await self._http.get(f"{self.host}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def chat_stream(
        self,
        messages: list,
        tools: Optional[list] = None,
        temperature: float = 0.7,
        context_size: int = 8192,
        num_predict: int = 2048,
    ) -> AsyncGenerator[dict, None]:
        """Streaming chat completion with optional tool calling."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": context_size,
                "num_predict": num_predict,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            async with self._http.stream(
                "POST",
                f"{self.host}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        yield chunk
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield {"error": str(e)}

    async def chat(self, messages: list, tools: Optional[list] = None, temperature: float = 0.7) -> dict:
        """Non-streaming chat completion."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools
        try:
            resp = await self._http.post(f"{self.host}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return {"error": str(e)}

    async def embed(self, text: str, model: str = "nomic-embed-text") -> list:
        """Get embedding vector for text."""
        try:
            resp = await self._http.post(
                f"{self.host}/api/embed",
                json={"model": model, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("embeddings", [data.get("embedding", [])])[0]
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return []

    async def check_connection(self) -> bool:
        """Check if Ollama is running and reachable."""
        try:
            resp = await self._http.get(f"{self.host}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self._http.aclose()
