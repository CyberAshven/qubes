"""
Venice.ai Provider Implementation

Privacy-first AI provider with OpenAI-compatible API.
Venice routes requests through decentralized GPU infrastructure
without logging prompts or responses.

Features:
- No data logging or storage
- Uncensored models
- Built-in web search
- Access to frontier models via privacy proxy

API Docs: https://docs.venice.ai/api-reference/api-spec
"""

from typing import List, Dict, Any, Optional, AsyncIterator
import json

from ai.providers.base import AIModelInterface, ModelResponse
from ai.retry_decorators import openai_retry
from ai.prompt_tools import get_prompt_tool_handler
from core.exceptions import AIError, ModelAPIError, ModelRateLimitError, ModelNotAvailableError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)


class VeniceModel(AIModelInterface):
    """
    Venice.ai model provider

    Privacy-first AI with OpenAI-compatible API.
    Prompts and responses are never logged or stored.
    """

    BASE_URL = "https://api.venice.ai/api/v1"

    # Pricing per 1M tokens (approximate, varies by model)
    # Venice pricing: https://venice.ai/pricing
    PRICING = {
        "venice-uncensored": {"input": 0.20, "output": 0.20},
        "llama-3.3-70b": {"input": 0.35, "output": 0.40},
        "qwen3-235b": {"input": 0.50, "output": 0.50},
        "qwen3-4b": {"input": 0.05, "output": 0.05},
        "deepseek-r1-llama-70b": {"input": 0.35, "output": 0.40},
        "mistral-31-24b": {"input": 0.15, "output": 0.15},
        # Legacy aliases
        "dolphin-2.9.3-mistral-7b": {"input": 0.20, "output": 0.20},
    }

    CONTEXT_WINDOWS = {
        "venice-uncensored": 131072,
        "llama-3.3-70b": 65536,
        "qwen3-235b": 131072,
        "qwen3-4b": 131072,
        "deepseek-r1-llama-70b": 131072,
        "mistral-31-24b": 131072,
        # Legacy aliases
        "dolphin-2.9.3-mistral-7b": 131072,
    }

    # Models that DON'T support tool/function calling
    # Most Venice models DO support tools - these are the exceptions
    TOOL_INCAPABLE_MODELS = {
        "venice-uncensored",
        "hermes-3-llama-3.1-405b",
        "deepseek-v3.2",
        # Legacy aliases
        "dolphin-2.9.3-mistral-7b",
    }

    def __init__(self, model_name: str, api_key: str, **kwargs):
        """
        Initialize Venice provider

        Args:
            model_name: Venice model ID
            api_key: Venice API key
            **kwargs: Additional parameters including:
                - enable_web_search: "off" | "auto" (default: "off")
                - character_slug: Optional character persona
        """
        super().__init__(model_name, api_key, **kwargs)

        # Venice-specific options
        self.enable_web_search = kwargs.get("enable_web_search", "off")
        self.character_slug = kwargs.get("character_slug", None)

        logger.info(
            "venice_model_initialized",
            model=model_name,
            web_search=self.enable_web_search
        )

    @openai_retry(max_attempts=3)
    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response using Venice API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL
            )

            # Build request parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Track if we're using prompt-based tools
            using_prompt_tools = False
            prompt_tool_handler = None

            # Most Venice models support tools, but a few don't (like venice-uncensored)
            if tools and self.model_name not in self.TOOL_INCAPABLE_MODELS:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            elif tools:
                # Use prompt-based tool calling for models without native support
                prompt_tool_handler = get_prompt_tool_handler()
                params["messages"] = prompt_tool_handler.inject_tools_into_messages(
                    messages, tools
                )
                using_prompt_tools = True
                logger.info(
                    "venice_using_prompt_tools",
                    model=self.model_name,
                    tools_count=len(tools),
                    reason="Model doesn't support native function calling, using prompt injection"
                )

            # Add Venice-specific parameters
            venice_params = {}

            web_search = kwargs.get("enable_web_search", self.enable_web_search)
            if web_search and web_search != "off":
                venice_params["enable_web_search"] = web_search
                venice_params["enable_web_citations"] = True

            character = kwargs.get("character_slug", self.character_slug)
            if character:
                venice_params["character_slug"] = character

            if kwargs.get("strip_thinking", False):
                venice_params["strip_thinking_response"] = True

            if venice_params:
                params["extra_body"] = {"venice_parameters": venice_params}

            # Add any extra parameters
            for key, value in kwargs.items():
                if key not in ["enable_web_search", "character_slug", "strip_thinking"]:
                    params[key] = value

            # Record API call start
            MetricsRecorder.record_ai_api_call("venice", self.model_name, "started")

            # Make API call
            response = await client.chat.completions.create(**params)

            # Record success
            MetricsRecorder.record_ai_api_call("venice", self.model_name, "success")

            # Parse response
            choice = response.choices[0]
            message = choice.message

            # Extract tool calls if present
            tool_calls = None
            content = message.content or ""

            if message.tool_calls:
                # Native tool calls from API
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "name": tc.function.name,
                        "parameters": json.loads(tc.function.arguments)
                    }
                    for tc in message.tool_calls
                ]
            elif using_prompt_tools and prompt_tool_handler:
                # Parse tool calls from model's text response
                parsed_calls = prompt_tool_handler.parse_tool_calls(content)
                if parsed_calls:
                    tool_calls = prompt_tool_handler.convert_to_native_format(parsed_calls)
                    # Extract clean content without tool call tags
                    content = prompt_tool_handler.extract_content_without_tool_calls(content)
                    logger.info(
                        "venice_prompt_tools_parsed",
                        model=self.model_name,
                        tool_calls_found=len(tool_calls),
                        tool_names=[tc["name"] for tc in tool_calls]
                    )

            # Record cost
            if response.usage:
                cost = self.estimate_cost(
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
                MetricsRecorder.record_ai_cost(cost, "venice", self.model_name)

            logger.debug(
                "venice_generation_complete",
                model=self.model_name,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                tool_calls=len(tool_calls) if tool_calls else 0
            )

            return ModelResponse(
                content=content,
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
            MetricsRecorder.record_ai_api_call("venice", self.model_name, "error")
            logger.error("venice_generation_failed", model=self.model_name, exc_info=True)

            # Classify error
            error_msg = str(e).lower()
            if "rate_limit" in error_msg or "429" in error_msg:
                raise ModelRateLimitError(
                    f"Venice rate limit exceeded: {str(e)}",
                    context={"model": self.model_name},
                    cause=e
                )
            elif "unauthorized" in error_msg or "401" in error_msg:
                raise ModelNotAvailableError(
                    f"Venice authentication failed: {str(e)}",
                    context={"model": self.model_name},
                    cause=e
                )
            else:
                raise ModelAPIError(
                    f"Venice API error: {str(e)}",
                    context={"model": self.model_name},
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
        """Stream response using Venice API"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL
            )

            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Most Venice models support tools, but a few don't (like venice-uncensored)
            if tools and self.model_name not in self.TOOL_INCAPABLE_MODELS:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            elif tools:
                # Use prompt-based tool calling for streaming too
                # Note: Tool call parsing happens on the complete response
                prompt_tool_handler = get_prompt_tool_handler()
                params["messages"] = prompt_tool_handler.inject_tools_into_messages(
                    messages, tools
                )
                logger.info(
                    "venice_stream_using_prompt_tools",
                    model=self.model_name,
                    tools_count=len(tools),
                    reason="Model doesn't support native function calling, using prompt injection"
                )

            # Add Venice-specific parameters
            venice_params = {}

            web_search = kwargs.get("enable_web_search", self.enable_web_search)
            if web_search and web_search != "off":
                venice_params["enable_web_search"] = web_search

            if venice_params:
                params["extra_body"] = {"venice_parameters": venice_params}

            MetricsRecorder.record_ai_api_call("venice", self.model_name, "started")

            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            MetricsRecorder.record_ai_api_call("venice", self.model_name, "success")

        except Exception as e:
            MetricsRecorder.record_ai_api_call("venice", self.model_name, "error")
            logger.error("venice_streaming_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"Venice streaming error: {str(e)}", cause=e)

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Parse tool calls from Venice response"""
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
        pricing = self.PRICING.get(self.model_name, {"input": 0.10, "output": 0.10})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "venice"
