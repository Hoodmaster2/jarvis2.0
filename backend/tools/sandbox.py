import logging
import asyncio
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SandboxError(Exception):
    pass


class ToolSandbox:
    def __init__(self, max_execution_time: float = 30.0, max_result_size: int = 1024 * 1024):
        self.max_execution_time = max_execution_time
        self.max_result_size = max_result_size

    async def execute(self, handler, tool_name: str, action_name: str, args: dict) -> dict:
        try:
            result = await asyncio.wait_for(
                handler(tool_name=tool_name, action=action_name, args=args),
                timeout=self.max_execution_time,
            )
            if isinstance(result, dict):
                result_str = str(result)
                if len(result_str) > self.max_result_size:
                    return {
                        "truncated": True,
                        "data": result_str[:self.max_result_size],
                        "original_size": len(result_str),
                    }
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Tool {tool_name}.{action_name} timed out after {self.max_execution_time}s")
            return {"error": f"Execution timed out after {self.max_execution_time}s"}
        except Exception as e:
            logger.error(f"Tool {tool_name}.{action_name} failed: {e}")
            return {"error": str(e)}
