"""
Anthropic Provider Implementation

Supports Claude 3.5, Claude 4, and Claude Opus models.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.1
"""

from typing import List, Dict, Any, Optional, AsyncIterator
import json

from ai.providers.base import AIModelInterface, ModelResponse
from ai.retry_decorators import anthropic_retry
from ai.circuit_breakers import with_circuit_breaker
from core.exceptions import AIError, ModelAPIError, ModelRateLimitError, ModelNotAvailableError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class AnthropicModel(AIModelInterface):
    """Anthropic Claude model provider"""

    # Pricing per 1M tokens (as of 2026)
    PRICING = {
        "claude-opus-4-6-20260204": {"input": 5.00, "output": 25.00},
        "claude-sonnet-4-6-20260217": {"input": 3.00, "output": 15.00},
        "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
        "claude-opus-4-1-20250805": {"input": 15.00, "output": 75.00},
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
        "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
    }

    CONTEXT_WINDOWS = {
        "claude-opus-4-6": 1000000,
        "claude-sonnet-4-6": 1000000,
        "claude-sonnet-4-5-20250929": 200000,
        "claude-opus-4-1-20250805": 200000,
        "claude-sonnet-4-20250514": 1000000,
        "claude-haiku-4-5-20251001": 200000,
        "claude-3-5-haiku-20241022": 200000,
    }

    @anthropic_retry(max_attempts=3)
    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
        **kwargs
    ) -> ModelResponse:
        """Generate response using Anthropic API with retry and circuit breaker"""
        try:
            from anthropic import AsyncAnthropic

            # Timeout: 120s for large models (Opus 4.6 with 1M context can be slow)
            client = AsyncAnthropic(api_key=self.api_key, timeout=120.0)

            # Anthropic requires max_tokens
            if not max_tokens:
                max_tokens = 4096

            # Convert messages to Anthropic format (extract system message + convert tool messages)
            system_message = None
            anthropic_messages = []


            for msg in messages:

                if msg["role"] == "system":
                    system_message = msg["content"]
                elif msg["role"] == "tool":
                    # Convert OpenAI tool format to Anthropic format
                    # OpenAI: {"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}
                    # Anthropic: {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]}
                    anthropic_messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": msg["content"]
                        }]
                    })
                elif msg["role"] == "assistant" and "tool_calls" in msg:
                    # Convert assistant message with tool_calls to Anthropic format
                    # OpenAI: {"role": "assistant", "content": "...", "tool_calls": [{...}]}
                    # Anthropic: {"role": "assistant", "content": [{"type": "text", "text": "..."}, {"type": "tool_use", ...}]}

                    content_blocks = []

                    # Add text content if present
                    if msg.get("content"):
                        content_blocks.append({
                            "type": "text",
                            "text": msg["content"]
                        })

                    # Convert tool_calls to tool_use blocks
                    for tool_call in msg["tool_calls"]:
                        # Parse arguments if they're a string
                        arguments = tool_call.get("function", {}).get("arguments", "{}")
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments)
                            except json.JSONDecodeError:
                                arguments = {}

                        content_blocks.append({
                            "type": "tool_use",
                            "id": tool_call["id"],
                            "name": tool_call.get("function", {}).get("name", "unknown"),
                            "input": arguments
                        })

                    anthropic_messages.append({
                        "role": "assistant",
                        "content": content_blocks
                    })
                else:
                    # Handle regular messages - check if content is already in Anthropic format
                    content = msg.get("content")

                    # If content is a list (multimodal message with images/text), pass through directly
                    # This handles vision messages from describe_my_appearance()
                    if isinstance(content, list):
                        anthropic_messages.append(msg)
                    else:
                        # Regular text message
                        anthropic_messages.append(msg)


            # Build request parameters
            params = {
                "model": self.model_name,
                "messages": anthropic_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            if system_message:
                params["system"] = system_message

            if tools:
                # Convert to Anthropic tool format
                params["tools"] = tools

            params.update(kwargs)

            # Record API call start
            MetricsRecorder.record_ai_api_call("anthropic", self.model_name, "started")

            # Make API call
            response = await client.messages.create(**params)

            # Record success
            MetricsRecorder.record_ai_api_call("anthropic", self.model_name, "success")

            # Parse response content
            content_text = ""
            tool_calls = []

            for content_block in response.content:
                if content_block.type == "text":
                    content_text += content_block.text
                elif content_block.type == "tool_use":
                    tool_calls.append({
                        "id": content_block.id,
                        "name": content_block.name,
                        "parameters": content_block.input
                    })

            # Record cost
            if response.usage:
                cost = self.estimate_cost(
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )
                MetricsRecorder.record_ai_cost(cost, "anthropic", self.model_name)

            logger.debug(
                "anthropic_generation_complete",
                model=self.model_name,
                input_tokens=response.usage.input_tokens if response.usage else None,
                output_tokens=response.usage.output_tokens if response.usage else None,
                tool_calls=len(tool_calls)
            )

            return ModelResponse(
                content=content_text,
                tool_calls=tool_calls if tool_calls else None,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                } if response.usage else None,
                finish_reason=response.stop_reason,
                raw_response=response
            )

        except Exception as e:
            MetricsRecorder.record_ai_api_call("anthropic", self.model_name, "error")
            logger.error("anthropic_generation_failed", model=self.model_name, exc_info=True)

            # Classify error with helpful messages
            error_msg = str(e).lower()
            error_str = str(e)

            if "rate_limit" in error_msg or "429" in error_msg or "overloaded" in error_msg:
                raise ModelRateLimitError(
                    f"Anthropic rate limit exceeded. Wait a moment and try again, or switch to a different model. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "rate_limit"},
                    cause=e
                )
            elif "unauthorized" in error_msg or "401" in error_msg or "invalid api key" in error_msg or "invalid x-api-key" in error_msg:
                raise ModelNotAvailableError(
                    f"Anthropic API key is invalid. Check your API key in Settings > API Keys. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "auth_failed"},
                    cause=e
                )
            elif "not_found" in error_msg or "does not exist" in error_msg or "invalid model" in error_msg:
                raise ModelNotAvailableError(
                    f"Model '{self.model_name}' not found in Anthropic's API. "
                    f"This model may require special access or has been renamed. Try 'claude-sonnet-4' or 'claude-3-5-haiku'. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "model_not_found"},
                    cause=e
                )
            elif "context" in error_msg and ("length" in error_msg or "too long" in error_msg or "exceed" in error_msg):
                raise ModelAPIError(
                    f"Message too long for model '{self.model_name}'. Try shortening your conversation. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "context_exceeded"},
                    cause=e
                )
            elif "safety" in error_msg or "content" in error_msg and "policy" in error_msg:
                raise ModelAPIError(
                    f"Content was flagged by Anthropic's safety systems. Try rephrasing your message. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "content_blocked"},
                    cause=e
                )
            elif "timeout" in error_msg or "timed out" in error_msg:
                # Raise as ModelNotAvailableError (NOT retryable) — retrying a timeout
                # just wastes another 120s. Let the user know immediately.
                raise ModelNotAvailableError(
                    f"Request to '{self.model_name}' timed out after 120s. "
                    f"This model may be too slow or Anthropic is under heavy load. Try again or use a faster model. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "timeout"},
                    cause=e
                )
            elif "credit" in error_msg or "billing" in error_msg or "payment" in error_msg:
                raise ModelNotAvailableError(
                    f"Anthropic account has billing or credit issues. Check your Anthropic account. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "billing"},
                    cause=e
                )
            elif "500" in error_msg or "internal server error" in error_msg or "api_error" in error_msg:
                # 500 errors are transient server-side issues - should be retried
                raise ModelAPIError(
                    f"Anthropic server error (500). This is a temporary issue on Anthropic's side. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "server_error", "retryable": True},
                    cause=e
                )
            else:
                raise ModelAPIError(
                    f"Anthropic API error with model '{self.model_name}': {error_str}",
                    context={"model": self.model_name, "error_type": "unknown"},
                    cause=e
                )

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response using Anthropic API"""
        try:
            from anthropic import AsyncAnthropic

            # Timeout: 120s for large models (Opus 4.6 with 1M context can be slow)
            client = AsyncAnthropic(api_key=self.api_key, timeout=120.0)

            if not max_tokens:
                max_tokens = 4096

            # Convert messages
            system_message = None
            anthropic_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append(msg)

            params = {
                "model": self.model_name,
                "messages": anthropic_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True
            }

            if system_message:
                params["system"] = system_message

            if tools:
                params["tools"] = tools

            params.update(kwargs)

            MetricsRecorder.record_ai_api_call("anthropic", self.model_name, "started")

            async with client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text

            MetricsRecorder.record_ai_api_call("anthropic", self.model_name, "success")

        except Exception as e:
            MetricsRecorder.record_ai_api_call("anthropic", self.model_name, "error")
            logger.error("anthropic_streaming_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"Anthropic streaming error: {str(e)}", cause=e)

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Parse tool calls from Anthropic response"""
        if not hasattr(response, 'content'):
            return []

        tool_calls = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_calls.append({
                    "id": content_block.id,
                    "name": content_block.name,
                    "parameters": content_block.input
                })

        return tool_calls

    def get_context_window(self) -> int:
        """Get context window size for model"""
        return self.CONTEXT_WINDOWS.get(self.model_name, 200000)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API call cost in USD"""
        pricing = self.PRICING.get(self.model_name, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
