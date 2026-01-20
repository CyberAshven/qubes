"""
NanoGPT Provider Implementation

Pay-per-prompt AI service with 760+ models.
Uses OpenAI-compatible API endpoint.
https://nano-gpt.com/api
"""

from typing import List, Dict, Any, Optional, AsyncIterator

from ai.providers.base import AIModelInterface, ModelResponse
from ai.retry_decorators import ai_api_retry
from core.exceptions import ModelAPIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class NanoGPTModel(AIModelInterface):
    """NanoGPT model provider (OpenAI-compatible API)"""

    def __init__(self, model_name: str, api_key: str, **kwargs):
        # Strip 'nanogpt/' prefix if present (registry uses nanogpt/model-name)
        if model_name.startswith("nanogpt/"):
            model_name = model_name[8:]  # Remove 'nanogpt/' prefix
        super().__init__(model_name, api_key, **kwargs)

    # Popular models with known pricing (per million tokens)
    # NanoGPT has 760+ models - these are just common ones
    PRICING = {
        # GPT models
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        # Claude models
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        # Open source models (typically cheaper)
        "llama-3.1-70b": {"input": 0.50, "output": 0.50},
        "llama-3.1-8b": {"input": 0.10, "output": 0.10},
        "mistral-large": {"input": 2.00, "output": 6.00},
        "mixtral-8x7b": {"input": 0.24, "output": 0.24},
        # Default for unknown models
        "default": {"input": 1.00, "output": 3.00},
    }

    CONTEXT_WINDOWS = {
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "claude-3-5-sonnet": 200000,
        "claude-3-haiku": 200000,
        "llama-3.1-70b": 128000,
        "llama-3.1-8b": 128000,
        "mistral-large": 128000,
        "mixtral-8x7b": 32000,
        "default": 32000,
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
        """Generate response using NanoGPT API with retry"""
        try:
            from openai import AsyncOpenAI

            # NanoGPT uses OpenAI-compatible API
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://nano-gpt.com/api/v1"
            )

            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Tool calling support (if model supports it)
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            params.update(kwargs)

            MetricsRecorder.record_ai_api_call("nanogpt", self.model_name, "started")

            try:
                response = await client.chat.completions.create(**params)
            except Exception as api_err:
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
                logger.error("nanogpt_api_error", error=error_msg)
                raise

            MetricsRecorder.record_ai_api_call("nanogpt", self.model_name, "success")

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
                MetricsRecorder.record_ai_cost(cost, "nanogpt", self.model_name)

            logger.debug(
                "nanogpt_generation_complete",
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
            error_detail = str(e)
            if hasattr(e, 'response'):
                try:
                    error_body = e.response.json()
                    error_detail = f"{str(e)} - Response: {error_body}"
                except:
                    pass

            MetricsRecorder.record_ai_api_call("nanogpt", self.model_name, "error")
            logger.error("nanogpt_generation_failed", model=self.model_name, error=error_detail, exc_info=True)

            # Classify error with helpful messages
            error_msg = error_detail.lower()
            if "rate_limit" in error_msg or "429" in error_msg or "too many" in error_msg:
                raise ModelRateLimitError(
                    f"NanoGPT rate limit exceeded. Wait a moment and try again. Original error: {error_detail}",
                    context={"model": self.model_name, "error_type": "rate_limit"},
                    cause=e
                )
            elif "unauthorized" in error_msg or "401" in error_msg or "invalid" in error_msg and "key" in error_msg:
                raise ModelNotAvailableError(
                    f"NanoGPT API key is invalid. Check your API key in Settings > API Keys. Original error: {error_detail}",
                    context={"model": self.model_name, "error_type": "auth_failed"},
                    cause=e
                )
            elif "model" in error_msg and ("not found" in error_msg or "invalid" in error_msg):
                raise ModelNotAvailableError(
                    f"Model '{self.model_name}' not available on NanoGPT. Check available models at nano-gpt.com. Original error: {error_detail}",
                    context={"model": self.model_name, "error_type": "model_not_found"},
                    cause=e
                )
            elif "credit" in error_msg or "balance" in error_msg or "billing" in error_msg:
                raise ModelNotAvailableError(
                    f"NanoGPT account has insufficient credits. Add credits at nano-gpt.com. Original error: {error_detail}",
                    context={"model": self.model_name, "error_type": "billing"},
                    cause=e
                )
            else:
                raise ModelAPIError(
                    f"NanoGPT API error with model '{self.model_name}': {error_detail}",
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
        """Stream response using NanoGPT API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://nano-gpt.com/api/v1"
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

            MetricsRecorder.record_ai_api_call("nanogpt", self.model_name, "started")

            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            MetricsRecorder.record_ai_api_call("nanogpt", self.model_name, "success")

        except Exception as e:
            MetricsRecorder.record_ai_api_call("nanogpt", self.model_name, "error")
            logger.error("nanogpt_streaming_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"NanoGPT streaming error: {str(e)}", cause=e)

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Parse tool calls from NanoGPT response (OpenAI format)"""
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
        return self.CONTEXT_WINDOWS.get(self.model_name, self.CONTEXT_WINDOWS["default"])

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API call cost in USD"""
        pricing = self.PRICING.get(self.model_name, self.PRICING["default"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
