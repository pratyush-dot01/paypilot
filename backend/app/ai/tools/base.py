"""
Base Tool Definition for PayPilot AI Agent (Phase 5).
Provides strict typing, Pydantic input validation, and execution interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger("paypilot.ai.tools.base")

class BaseTool(ABC):
    """Abstract base class for all PayPilot agent tools."""

    name: str = ""
    description: str = ""
    input_schema: Type[BaseModel] = BaseModel
    requires_confirmation: bool = False

    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with validated keyword arguments."""
        pass

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate inputs against input_schema and execute safely.
        Never allows unhandled exceptions to crash the agent.
        """
        try:
            # Validate input using Pydantic schema
            validated = self.input_schema(**arguments)
            clean_args = validated.model_dump()
            result = await self.run(**clean_args)
            return {
                "tool_name": self.name,
                "arguments": clean_args,
                "success": True,
                "result": result,
                "error": None,
            }
        except Exception as e:
            logger.error(f"Error executing tool '{self.name}': {e}", exc_info=True)
            return {
                "tool_name": self.name,
                "arguments": arguments,
                "success": False,
                "result": None,
                "error": str(e),
            }

    def to_function_def(self) -> Dict[str, Any]:
        """Generate OpenAI/Gemini function declaration schema."""
        schema = self.input_schema.model_json_schema()
        # Clean up Pydantic json schema for LLM tools
        schema.pop("title", None)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema,
        }

