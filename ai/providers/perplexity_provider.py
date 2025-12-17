"""
Perplexity Provider Implementation

Supports Sonar models with web search capabilities.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.1
"""

from typing import List, Dict, Any, Optional, AsyncIterator

from ai.providers.base import AIModelInterface, ModelResponse
from ai.retry_decorators import perplexity_retry
from ai.circuit_breakers import with_circuit_breaker
from core.exceptions import ModelAPIError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class PerplexityModel(AIModelInterface):
    """Perplexity Sonar model provider (OpenAI-compatible API)"""

    PRICING = {
        "sonar-pro": {"input": 3.00, "output": 15.00},
        "sonar": {"input": 0.20, "output": 0.20},
        "sonar-reasoning-pro": {"input": 5.00, "output": 20.00},
        "sonar-reasoning": {"input": 1.00, "output": 5.00},
        "sonar-deep-research": {"input": 10.00, "output": 30.00},
    }

    CONTEXT_WINDOWS = {
        "sonar-pro": 127000,
        "sonar": 127000,
        "sonar-reasoning-pro": 127000,
        "sonar-reasoning": 127000,
        "sonar-deep-research": 127000,
    }

    @perplexity_retry(max_attempts=3)
    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response using Perplexity API with retry and circuit breaker"""
        try:
            from openai import AsyncOpenAI

            # Perplexity uses OpenAI-compatible API
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.perplexity.ai"
            )

            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Perplexity tool calling support varies by model
            # As of Jan 2025, sonar models don't support tool calling
            # Only include tools if model supports them
            supports_tools = self.model_name in ["sonar-reasoning-pro", "sonar-reasoning"]
            if tools and supports_tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            elif tools and not supports_tools:
                logger.debug(f"perplexity_tools_skipped", model=self.model_name, reason="Model doesn't support tool calling")

            params.update(kwargs)

            MetricsRecorder.record_ai_api_call("perplexity", self.model_name, "started")

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
                raise

            MetricsRecorder.record_ai_api_call("perplexity", self.model_name, "success")

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
                MetricsRecorder.record_ai_cost(cost, "perplexity", self.model_name)

            logger.debug(
                "perplexity_generation_complete",
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
            # Try to extract actual error message from HTTPStatusError
            error_detail = str(e)
            if hasattr(e, 'response'):
                try:
                    error_body = e.response.json()
                    error_detail = f"{str(e)} - Response: {error_body}"
                except:
                    pass

            MetricsRecorder.record_ai_api_call("perplexity", self.model_name, "error")
            logger.error("perplexity_generation_failed", model=self.model_name, error=error_detail, exc_info=True)
            raise ModelAPIError(f"Perplexity API error: {error_detail}", cause=e)

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response using Perplexity API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.perplexity.ai"
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

            MetricsRecorder.record_ai_api_call("perplexity", self.model_name, "started")

            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            MetricsRecorder.record_ai_api_call("perplexity", self.model_name, "success")

        except Exception as e:
            MetricsRecorder.record_ai_api_call("perplexity", self.model_name, "error")
            logger.error("perplexity_streaming_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"Perplexity streaming error: {str(e)}", cause=e)

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Parse tool calls from Perplexity response (OpenAI format)"""
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
        return self.CONTEXT_WINDOWS.get(self.model_name, 127000)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API call cost in USD"""
        pricing = self.PRICING.get(self.model_name, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
