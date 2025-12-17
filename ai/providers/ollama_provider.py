"""
Ollama Provider Implementation

Supports local LLMs running on Ollama (Llama, Qwen, DeepSeek, etc.).
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.1
"""

from typing import List, Dict, Any, Optional, AsyncIterator

from ai.providers.base import AIModelInterface, ModelResponse
from ai.retry_decorators import ollama_retry
from ai.circuit_breakers import with_circuit_breaker
from core.exceptions import ModelAPIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class OllamaModel(AIModelInterface):
    """Ollama local model provider (OpenAI-compatible API)"""

    CONTEXT_WINDOWS = {
        "llama3.3:70b": 128000,
        "qwen3:235b": 32768,
        "qwen3:30b": 32768,
        "qwen2.5:7b": 32768,
        "deepseek-r1:8b": 32768,
        "phi4:14b": 16384,
        "gemma2:9b": 8192,
        "mistral:7b": 8192,
        "codellama:7b": 16384,
    }

    def __init__(self, model_name: str, api_key: str = "ollama", base_url: str = "http://localhost:11434/v1", **kwargs):
        """
        Initialize Ollama provider

        Args:
            model_name: Model name (e.g., "llama3.3:70b")
            api_key: Not required for Ollama, defaults to "ollama"
            base_url: Ollama API endpoint
        """
        super().__init__(model_name, api_key, **kwargs)
        self.base_url = base_url

    @ollama_retry(max_attempts=2)
    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response using Ollama API with retry and circuit breaker"""
        try:
            from openai import AsyncOpenAI

            # Ollama uses OpenAI-compatible API
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Ollama supports tool calling (OpenAI format)
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            params.update(kwargs)

            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "started")

            response = await client.chat.completions.create(**params)

            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "success")

            # Parse response (OpenAI-compatible format)
            choice = response.choices[0]
            message = choice.message

            tool_calls = None
            if message.tool_calls:
                import json
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "parameters": json.loads(tc.function.arguments)
                    }
                    for tc in message.tool_calls
                ]

            # Ollama is free (local), so cost is 0
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }

            logger.debug(
                "ollama_generation_complete",
                model=self.model_name,
                input_tokens=usage["prompt_tokens"] if usage else None,
                output_tokens=usage["completion_tokens"] if usage else None,
                tool_calls=len(tool_calls) if tool_calls else 0
            )

            return ModelResponse(
                content=message.content or "",
                tool_calls=tool_calls,
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason,
                raw_response=response
            )

        except Exception as e:
            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "error")
            logger.error("ollama_generation_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"Ollama API error: {str(e)}", cause=e)

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response using Ollama API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            params.update(kwargs)

            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "started")

            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "success")

        except Exception as e:
            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "error")
            logger.error("ollama_streaming_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"Ollama streaming error: {str(e)}", cause=e)

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Parse tool calls from Ollama response (OpenAI format)"""
        import json

        if not hasattr(response, 'choices') or not response.choices:
            return []

        message = response.choices[0].message
        if not message.tool_calls:
            return []

        return [
            {
                "id": tc.id,
                "name": tc.function.name,
                "parameters": json.loads(tc.function.arguments)
            }
            for tc in message.tool_calls
        ]

    def get_context_window(self) -> int:
        """Get context window size for model"""
        return self.CONTEXT_WINDOWS.get(self.model_name, 8192)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Ollama is free (local models), so cost is always 0"""
        return 0.0
