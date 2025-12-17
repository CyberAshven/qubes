"""
Base AI Model Provider Interface

Abstract base class for all AI model providers.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.1
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass

from core.exceptions import AIError
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ModelResponse:
    """Standardized model response across all providers"""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Any] = None


class AIModelInterface(ABC):
    """
    Abstract base class for all AI models

    All providers must implement this interface for consistent interaction
    across OpenAI, Anthropic, Google, Perplexity, DeepSeek, and Ollama.
    """

    def __init__(self, model_name: str, api_key: str, **kwargs):
        """
        Initialize AI model provider

        Args:
            model_name: Model identifier (e.g., "gpt-4o", "claude-sonnet-4")
            api_key: API key for authentication
            **kwargs: Additional provider-specific parameters
        """
        self.model_name = model_name
        self.api_key = api_key
        self.extra_params = kwargs

        logger.info(
            "ai_model_initialized",
            model=model_name,
            provider=self.__class__.__name__.replace("Model", "").lower()
        )

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """
        Generate response with optional tool calling

        Args:
            messages: Conversation messages in OpenAI format
            tools: Available tools in provider-specific format
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            ModelResponse with content and optional tool calls

        Raises:
            AIError: If generation fails
        """
        raise NotImplementedError

    @abstractmethod
    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream response with optional tool calling

        Args:
            messages: Conversation messages
            tools: Available tools
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Yields:
            Response chunks as they arrive

        Raises:
            AIError: If streaming fails
        """
        raise NotImplementedError

    @abstractmethod
    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """
        Parse tool calls from model response

        Args:
            response: Raw provider response

        Returns:
            List of tool calls with format:
            [
                {
                    "id": "call_123",
                    "name": "web_search",
                    "parameters": {"query": "..."}
                }
            ]
        """
        raise NotImplementedError

    def get_provider_name(self) -> str:
        """Get provider name (openai, anthropic, google, etc.)"""
        return self.__class__.__name__.replace("Model", "").lower()

    def supports_streaming(self) -> bool:
        """Check if provider supports streaming"""
        return True

    def supports_tool_calling(self) -> bool:
        """Check if provider supports tool/function calling"""
        return True

    def get_context_window(self) -> int:
        """Get maximum context window size in tokens"""
        # Default, override in subclasses
        return 8192

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate API call cost in USD

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Default implementation, override in subclasses with actual pricing
        return 0.0
