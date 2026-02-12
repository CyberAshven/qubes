"""
DeepSeek Provider Implementation

Supports DeepSeek-V3.2 (deepseek-chat) and DeepSeek-R1 (deepseek-reasoner).
Uses OpenAI-compatible API endpoint.
"""

from typing import List, Dict, Any, Optional, AsyncIterator

from ai.providers.base import AIModelInterface, ModelResponse
from ai.retry_decorators import ai_api_retry
from ai.circuit_breakers import with_circuit_breaker
from core.exceptions import ModelAPIError, ModelNotAvailableError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class DeepSeekModel(AIModelInterface):
    """DeepSeek model provider (OpenAI-compatible API)"""

    PRICING = {
        "deepseek-chat": {"input": 0.27, "output": 1.10},  # Per million tokens
        "deepseek-reasoner": {"input": 0.55, "output": 2.19},  # R1 reasoning model
    }

    CONTEXT_WINDOWS = {
        "deepseek-chat": 64000,  # 64k context
        "deepseek-reasoner": 64000,  # 64k context + 32k reasoning tokens
    }

    @ai_api_retry()
    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response using DeepSeek API with retry and circuit breaker"""
        try:
            from openai import AsyncOpenAI

            # DeepSeek uses OpenAI-compatible API
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )

            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # DeepSeek supports tool calling (function calling)
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            params.update(kwargs)

            MetricsRecorder.record_ai_api_call("deepseek", self.model_name, "started")

            try:
                response = await client.chat.completions.create(**params)
            except Exception as api_err:
                # Extract error details from API response
                error_msg = str(api_err)
                if hasattr(api_err, 'response') and api_err.response is not None:
                    try:
                        error_body = api_err.response.json()
                        error_msg = f"{error_msg} | Response body: {error_body}"
                    except:
                        try:
                            error_text = api_err.response.text
                            error_msg = f"{error_msg} | Response text: {error_text}"
                        except:
                            pass
                logger.error("deepseek_api_error", error=error_msg)
                raise

            MetricsRecorder.record_ai_api_call("deepseek", self.model_name, "success")

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

            # Record cost
            if response.usage:
                cost = self.estimate_cost(
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
                MetricsRecorder.record_ai_cost(cost, "deepseek", self.model_name)

            # DeepSeek-R1 (reasoner) includes reasoning_content in response
            reasoning_content = None
            if self.model_name == "deepseek-reasoner" and hasattr(message, 'reasoning_content'):
                reasoning_content = message.reasoning_content

            logger.debug(
                "deepseek_generation_complete",
                model=self.model_name,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                tool_calls=len(tool_calls) if tool_calls else 0,
                has_reasoning=reasoning_content is not None
            )

            response_dict = {
                "content": message.content or "",
                "tool_calls": tool_calls,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                } if response.usage else None,
                "finish_reason": choice.finish_reason,
                "raw_response": response
            }

            # Include reasoning content for deepseek-reasoner
            if reasoning_content:
                response_dict["reasoning_content"] = reasoning_content

            return ModelResponse(**response_dict)

        except Exception as e:
            # Try to extract actual error message from HTTPStatusError
            error_detail = str(e)
            if hasattr(e, 'response'):
                try:
                    error_body = e.response.json()
                    error_detail = f"{str(e)} - Response: {error_body}"
                except:
                    pass

            MetricsRecorder.record_ai_api_call("deepseek", self.model_name, "error")
            logger.error("deepseek_generation_failed", model=self.model_name, error=error_detail, exc_info=True)

            # Classify error with helpful messages
            error_msg = error_detail.lower()
            if "rate_limit" in error_msg or "429" in error_msg or "too many" in error_msg:
                raise ModelRateLimitError(
                    f"DeepSeek rate limit exceeded. Wait a moment and try again. Original error: {error_detail}",
                    context={"model": self.model_name, "error_type": "rate_limit"},
                    cause=e
                )
            elif "unauthorized" in error_msg or "401" in error_msg or "invalid" in error_msg and "key" in error_msg:
                raise ModelNotAvailableError(
                    f"DeepSeek API key is invalid. Check your API key in Settings > API Keys. Original error: {error_detail}",
                    context={"model": self.model_name, "error_type": "auth_failed"},
                    cause=e
                )
            elif "balance" in error_msg or "insufficient" in error_msg:
                raise ModelNotAvailableError(
                    f"DeepSeek account has insufficient balance. Add credits at platform.deepseek.com. Original error: {error_detail}",
                    context={"model": self.model_name, "error_type": "billing"},
                    cause=e
                )
            elif "context" in error_msg and "length" in error_msg:
                raise ModelAPIError(
                    f"Message too long for DeepSeek model. Try shortening your conversation. Original error: {error_detail}",
                    context={"model": self.model_name, "error_type": "context_exceeded"},
                    cause=e
                )
            else:
                raise ModelAPIError(
                    f"DeepSeek API error with model '{self.model_name}': {error_detail}",
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
        """Stream response using DeepSeek API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
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

            MetricsRecorder.record_ai_api_call("deepseek", self.model_name, "started")

            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            MetricsRecorder.record_ai_api_call("deepseek", self.model_name, "success")

        except Exception as e:
            MetricsRecorder.record_ai_api_call("deepseek", self.model_name, "error")
            logger.error("deepseek_streaming_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"DeepSeek streaming error: {str(e)}", cause=e)

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Parse tool calls from DeepSeek response (OpenAI format)"""
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
        return self.CONTEXT_WINDOWS.get(self.model_name, 64000)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API call cost in USD"""
        pricing = self.PRICING.get(self.model_name, {"input": 0.27, "output": 1.10})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
