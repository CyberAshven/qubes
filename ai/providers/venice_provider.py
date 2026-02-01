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
import re

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
        "llama-3.2-3b": {"input": 0.05, "output": 0.05},
        "qwen3-235b-a22b-instruct-2507": {"input": 0.50, "output": 0.50},
        "qwen3-235b-a22b-thinking-2507": {"input": 0.60, "output": 0.60},
        "qwen3-next-80b": {"input": 0.40, "output": 0.45},
        "qwen3-coder-480b-a35b-instruct": {"input": 0.70, "output": 0.75},
        "qwen3-4b": {"input": 0.05, "output": 0.05},
        "mistral-31-24b": {"input": 0.15, "output": 0.15},
        "claude-opus-45": {"input": 1.50, "output": 7.50},
        "openai-gpt-52": {"input": 1.75, "output": 7.00},
        "openai-gpt-oss-120b": {"input": 0.50, "output": 0.50},
        "gemini-3-pro-preview": {"input": 1.00, "output": 2.00},
        "gemini-3-flash-preview": {"input": 0.30, "output": 0.60},
        "grok-41-fast": {"input": 0.50, "output": 0.50},
        "grok-code-fast-1": {"input": 0.50, "output": 0.50},
        "zai-org-glm-4.7": {"input": 0.40, "output": 0.45},
        "kimi-k2-thinking": {"input": 0.50, "output": 0.60},
        "minimax-m21": {"input": 0.30, "output": 0.35},
        "deepseek-v3.2": {"input": 0.35, "output": 0.40},
        "google-gemma-3-27b-it": {"input": 0.15, "output": 0.20},
        "hermes-3-llama-3.1-405b": {"input": 0.60, "output": 0.70},
        # Legacy aliases
        "dolphin-2.9.3-mistral-7b": {"input": 0.20, "output": 0.20},
    }

    CONTEXT_WINDOWS = {
        "venice-uncensored": 131072,
        "llama-3.3-70b": 131072,
        "llama-3.2-3b": 131072,
        "qwen3-235b-a22b-instruct-2507": 131072,
        "qwen3-235b-a22b-thinking-2507": 131072,
        "qwen3-next-80b": 131072,
        "qwen3-coder-480b-a35b-instruct": 131072,
        "qwen3-4b": 131072,
        "mistral-31-24b": 131072,
        "claude-opus-45": 200000,
        "openai-gpt-52": 256000,
        "openai-gpt-oss-120b": 131072,
        "gemini-3-pro-preview": 1000000,
        "gemini-3-flash-preview": 1000000,
        "grok-41-fast": 131072,
        "grok-code-fast-1": 131072,
        "zai-org-glm-4.7": 131072,
        "kimi-k2-thinking": 131072,
        "minimax-m21": 131072,
        "deepseek-v3.2": 131072,
        "google-gemma-3-27b-it": 131072,
        "hermes-3-llama-3.1-405b": 131072,
        # Legacy aliases
        "dolphin-2.9.3-mistral-7b": 131072,
    }

    # Models that DON'T support tool/function calling
    # Most Venice models DO support tools - these are the exceptions
    # These will use prompt-based tool calling instead
    TOOL_INCAPABLE_MODELS = {
        "venice-uncensored",
        "hermes-3-llama-3.1-405b",
        "deepseek-v3.2",
        "grok-code-fast-1",         # Code-focused, no native tools
        "llama-3.2-3b",             # Small model, limited tool support
        "llama-3.3-70b",            # Llama through Venice proxy - use prompt-based
        "kimi-k2-thinking",         # No native tools, but prompt-based works for tool calls
        "qwen3-4b",                 # Small model, limited tool support
        "qwen3-235b-a22b-thinking-2507",  # Thinking models should use prompt-based
        "google-gemma-3-27b-it",    # Gemma has weak native tool support
        # Models proxied through Venice use their native format, not OpenAI format
        "claude-opus-45",           # Claude uses Anthropic format
        "openai-gpt-52",            # GPT through Venice proxy
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
        # Map registry names to actual Venice API model names
        # This allows using unique registry keys while sending correct names to Venice
        MODEL_NAME_MAP = {
            "venice/gemini-3-pro": "gemini-3-pro-preview",
            "venice/gemini-3-flash": "gemini-3-flash-preview",
        }
        actual_model_name = MODEL_NAME_MAP.get(model_name, model_name)

        super().__init__(actual_model_name, api_key, **kwargs)

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

            # Use longer timeout for thinking models which may take more time
            is_thinking_model = "thinking" in self.model_name.lower()
            timeout = 120.0 if is_thinking_model else 60.0

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL,
                timeout=timeout
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
                    messages, tools, model_name=self.model_name
                )
                using_prompt_tools = True
                tool_names = [t.get("function", {}).get("name", "?") for t in tools]
                logger.info(
                    "venice_using_prompt_tools",
                    model=self.model_name,
                    tools_count=len(tools),
                    tool_names=tool_names,
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

            # Only strip thinking if explicitly requested
            # Note: Auto-stripping for thinking models was causing empty responses
            # because Venice would strip all output if the model only produced thinking
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

            # Debug logging to diagnose empty responses
            raw_content = message.content
            raw_tool_calls = message.tool_calls
            logger.info(
                "venice_raw_response",
                model=self.model_name,
                finish_reason=choice.finish_reason,
                content_length=len(raw_content) if raw_content else 0,
                content_preview=raw_content[:500] if raw_content else "(empty)",
                has_tool_calls=bool(raw_tool_calls),
                tool_call_count=len(raw_tool_calls) if raw_tool_calls else 0
            )

            # Extract tool calls if present
            tool_calls = None
            content = message.content or ""

            # Strip [Thinking: ...] blocks that some Venice models output
            # These are internal reasoning that shouldn't be shown to users
            thinking_pattern = r'\[Thinking:.*?\]'
            if re.search(thinking_pattern, content, re.DOTALL | re.IGNORECASE):
                original_content = content
                content = re.sub(thinking_pattern, '', content, flags=re.DOTALL | re.IGNORECASE).strip()
                logger.info(
                    "venice_thinking_stripped",
                    model=self.model_name,
                    had_thinking=True,
                    remaining_content_length=len(content)
                )
                # If only thinking was present (no actual response), raise error to trigger retry
                if not content and not message.tool_calls:
                    logger.warning(
                        "venice_only_thinking_no_response",
                        model=self.model_name,
                        original_preview=original_content[:200]
                    )
                    raise ModelAPIError(
                        f"Model '{self.model_name}' returned only thinking blocks with no actual response. Retrying...",
                        context={"model": self.model_name, "error_type": "empty_response"}
                    )

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
                else:
                    # Model had tools available but didn't use them
                    # Check if response looks like it SHOULD have had a tool call
                    has_tool_keywords = any(kw in content.lower() for kw in [
                        "switch", "model", "search", "remember", "send"
                    ])
                    logger.warning(
                        "venice_prompt_tools_not_used",
                        model=self.model_name,
                        response_preview=content[:200] if content else "(empty)",
                        has_tool_keywords=has_tool_keywords,
                        hint="Model may have narrated action instead of calling tool"
                    )
            else:
                # Fallback: some models (like Kimi K2) output tool calls as text
                # even when native tools are expected. Check for text-based tool calls.
                fallback_handler = get_prompt_tool_handler()
                if fallback_handler.has_tool_call(content):
                    parsed_calls = fallback_handler.parse_tool_calls(content)
                    if parsed_calls:
                        tool_calls = fallback_handler.convert_to_native_format(parsed_calls)
                        content = fallback_handler.extract_content_without_tool_calls(content)
                        logger.info(
                            "venice_text_tool_calls_fallback",
                            model=self.model_name,
                            tool_calls_found=len(tool_calls),
                            tool_names=[tc["name"] for tc in tool_calls],
                            hint="Model output tool calls as text instead of native format"
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

            # Final check: if no content and no tool calls, raise error to trigger retry
            # This can happen if the model returns empty/null content
            if not content and not tool_calls:
                # Include raw content info for debugging
                raw_info = f"raw_content={'(empty)' if not raw_content else repr(raw_content[:200])}, finish_reason={choice.finish_reason}"
                logger.warning(
                    "venice_empty_response",
                    model=self.model_name,
                    finish_reason=choice.finish_reason,
                    raw_content_length=len(raw_content) if raw_content else 0,
                    raw_content_preview=raw_content[:200] if raw_content else "(empty)"
                )
                raise ModelAPIError(
                    f"Model '{self.model_name}' returned empty response ({raw_info})",
                    context={"model": self.model_name, "error_type": "empty_response", "finish_reason": choice.finish_reason, "raw_content_preview": raw_content[:200] if raw_content else None}
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

            # Classify error with helpful messages
            error_msg = str(e).lower()
            error_str = str(e)

            if "rate_limit" in error_msg or "429" in error_msg or "too many" in error_msg:
                raise ModelRateLimitError(
                    f"Venice rate limit exceeded. Wait a moment and try again, or switch to a different model. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "rate_limit"},
                    cause=e
                )
            elif "unauthorized" in error_msg or "401" in error_msg or "invalid" in error_msg and "key" in error_msg:
                raise ModelNotAvailableError(
                    f"Venice API key is invalid. Check your API key in Settings > API Keys. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "auth_failed"},
                    cause=e
                )
            elif "model" in error_msg and ("not found" in error_msg or "not available" in error_msg or "invalid" in error_msg):
                raise ModelNotAvailableError(
                    f"Model '{self.model_name}' not available on Venice. Try a different model. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "model_not_found"},
                    cause=e
                )
            elif "credit" in error_msg or "balance" in error_msg or "billing" in error_msg:
                raise ModelNotAvailableError(
                    f"Venice account has insufficient credits. Add credits at venice.ai. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "billing"},
                    cause=e
                )
            elif "context" in error_msg and "length" in error_msg:
                raise ModelAPIError(
                    f"Message too long for Venice model. Try shortening your conversation. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "context_exceeded"},
                    cause=e
                )
            else:
                raise ModelAPIError(
                    f"Venice API error with model '{self.model_name}': {error_str}",
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
        """Stream response using Venice API"""
        try:
            from openai import AsyncOpenAI

            # Use longer timeout for thinking models which may take more time
            is_thinking_model = "thinking" in self.model_name.lower()
            timeout = 120.0 if is_thinking_model else 60.0

            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL,
                timeout=timeout
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
                    messages, tools, model_name=self.model_name
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
