"""
OpenAI Provider Implementation

Supports GPT-4, GPT-4o, GPT-5, o1/o3/o4 reasoning models, and DALL-E 3.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.1
"""

from typing import List, Dict, Any, Optional, AsyncIterator
import json

from ai.providers.base import AIModelInterface, ModelResponse
from ai.retry_decorators import openai_retry
from ai.circuit_breakers import with_circuit_breaker
from core.exceptions import AIError, ModelAPIError, ModelRateLimitError, ModelNotAvailableError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class OpenAIModel(AIModelInterface):
    """OpenAI GPT model provider"""

    # Pricing per 1M tokens (as of 2025)
    PRICING = {
        "gpt-5": {"input": 2.50, "output": 10.00},
        "gpt-5-mini": {"input": 0.15, "output": 0.60},
        "gpt-5-nano": {"input": 0.05, "output": 0.20},
        "gpt-5-codex": {"input": 3.00, "output": 12.00},
        "gpt-4.1": {"input": 10.00, "output": 30.00},
        "gpt-4.1-mini": {"input": 0.60, "output": 1.80},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "o4-mini": {"input": 1.10, "output": 4.40},
        "o3-mini": {"input": 1.00, "output": 4.00},
        "o1": {"input": 15.00, "output": 60.00},
    }

    CONTEXT_WINDOWS = {
        "gpt-5": 256000,
        "gpt-5-mini": 128000,
        "gpt-5-nano": 64000,
        "gpt-5-codex": 256000,
        "gpt-4.1": 1000000,
        "gpt-4.1-mini": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "o4-mini": 128000,
        "o3-mini": 128000,
        "o1": 200000,
    }

    @openai_retry(max_attempts=3)
    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response using OpenAI API with retry and circuit breaker"""
        try:
            from openai import AsyncOpenAI
            from ai.model_registry import ModelRegistry

            client = AsyncOpenAI(api_key=self.api_key)

            # Check if model has fixed temperature requirement
            model_info = ModelRegistry.get_model_info(self.model_name)
            if model_info and "temperature_fixed" in model_info:
                temperature = model_info["temperature_fixed"]
                logger.debug(
                    "temperature_override",
                    model=self.model_name,
                    original_temp=temperature,
                    fixed_temp=model_info["temperature_fixed"]
                )

            # Build request parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            # Add any extra parameters
            params.update(kwargs)

            # Record API call start
            MetricsRecorder.record_ai_api_call("openai", self.model_name, "started")

            # Make API call
            response = await client.chat.completions.create(**params)

            # Record success
            MetricsRecorder.record_ai_api_call("openai", self.model_name, "success")

            # Parse response
            choice = response.choices[0]
            message = choice.message

            # Extract tool calls if present
            tool_calls = None
            if message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "name": tc.function.name,
                        "parameters": json.loads(tc.function.arguments)
                    }
                    for tc in message.tool_calls
                ]

            # Record cost
            if response.usage:
                cost = self.estimate_cost(
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
                MetricsRecorder.record_ai_cost(cost, "openai", self.model_name)

            logger.debug(
                "openai_generation_complete",
                model=self.model_name,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                tool_calls=len(tool_calls) if tool_calls else 0
            )

            return ModelResponse(
                content=message.content or "",
                tool_calls=tool_calls,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                finish_reason=choice.finish_reason,
                raw_response=response
            )

        except Exception as e:
            MetricsRecorder.record_ai_api_call("openai", self.model_name, "error")
            logger.error("openai_generation_failed", model=self.model_name, exc_info=True)

            # Classify error with helpful messages
            error_msg = str(e).lower()
            error_str = str(e)

            if "rate_limit" in error_msg or "429" in error_msg or "too many requests" in error_msg:
                raise ModelRateLimitError(
                    f"OpenAI rate limit exceeded. Wait a moment and try again, or switch to a different model. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "rate_limit"},
                    cause=e
                )
            elif "unauthorized" in error_msg or "401" in error_msg or "invalid api key" in error_msg:
                raise ModelNotAvailableError(
                    f"OpenAI API key is invalid. Check your API key in Settings > API Keys. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "auth_failed"},
                    cause=e
                )
            elif "model_not_found" in error_msg or "does not exist" in error_msg or "invalid model" in error_msg:
                raise ModelNotAvailableError(
                    f"Model '{self.model_name}' not found in OpenAI's API. "
                    f"This model may require special access or has been renamed. Try 'gpt-4o' or 'gpt-4o-mini'. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "model_not_found"},
                    cause=e
                )
            elif "context_length" in error_msg or "maximum context" in error_msg or "too long" in error_msg:
                raise ModelAPIError(
                    f"Message too long for model '{self.model_name}'. Try shortening your conversation or using a model with larger context. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "context_exceeded"},
                    cause=e
                )
            elif "content_policy" in error_msg or "flagged" in error_msg or "moderation" in error_msg:
                raise ModelAPIError(
                    f"Content was flagged by OpenAI's content policy. Try rephrasing your message. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "content_blocked"},
                    cause=e
                )
            elif "timeout" in error_msg or "timed out" in error_msg:
                raise ModelAPIError(
                    f"Request timed out. OpenAI may be experiencing high load. Try again or use a faster model. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "timeout"},
                    cause=e
                )
            elif "insufficient_quota" in error_msg or "billing" in error_msg:
                raise ModelNotAvailableError(
                    f"OpenAI account has insufficient quota or billing issues. Check your OpenAI account billing. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "billing"},
                    cause=e
                )
            else:
                raise ModelAPIError(
                    f"OpenAI API error with model '{self.model_name}': {error_str}",
                    context={"model": self.model_name, "error_type": "unknown"},
                    cause=e
                )

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response using OpenAI API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

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

            MetricsRecorder.record_ai_api_call("openai", self.model_name, "started")

            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            MetricsRecorder.record_ai_api_call("openai", self.model_name, "success")

        except Exception as e:
            MetricsRecorder.record_ai_api_call("openai", self.model_name, "error")
            logger.error("openai_streaming_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"OpenAI streaming error: {str(e)}", cause=e)

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Parse tool calls from OpenAI response"""
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
        return self.CONTEXT_WINDOWS.get(self.model_name, 128000)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API call cost in USD"""
        pricing = self.PRICING.get(self.model_name, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
