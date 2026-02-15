"""
Ollama Provider Implementation

Supports local LLMs running on Ollama (Llama, Qwen, DeepSeek, etc.).
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.1
"""

from typing import List, Dict, Any, Optional, AsyncIterator
import json

from ai.providers.base import AIModelInterface, ModelResponse
from ai.retry_decorators import ollama_retry
from ai.prompt_tools import get_prompt_tool_handler
from ai.circuit_breakers import with_circuit_breaker
from core.exceptions import ModelAPIError, ModelNotAvailableError
from utils.logging import get_logger
from monitoring.metrics import MetricsRecorder

logger = get_logger(__name__)

# Track models we've already attempted to pull (avoid repeated pull attempts)
_pull_attempted: set = set()


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

    # Models that don't support native tool/function calling
    # These will use prompt-based tool calling instead
    # Most Ollama models work better with prompt-based tools
    TOOL_INCAPABLE_MODELS = {
        "llama3.3:70b",      # Large model, but native tools unreliable
        "codellama:7b",      # Code-focused, no function calling
        "codellama:13b",
        "codellama:34b",
        "llama3.2",          # Base model, native tools unreliable
        "llama3.2:1b",       # Very small, limited tool support
        "llama3.2:3b",
        "llama3.2-vision:11b",  # Vision models don't support native tools
        "llama3.2-vision:90b",
        "gemma2:9b",         # Gemma has weak native tool support
        "phi4:14b",          # Phi has inconsistent tool support
        "mistral:7b",
        "qwen2.5:7b",
        "qwen3:30b",
        "qwen3:235b",
        "deepseek-r1:8b",
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
            import httpx

            # Ollama uses OpenAI-compatible API
            # Timeout: 5s connect, 300s total (local models can be slow, especially reasoning models)
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=httpx.Timeout(300.0, connect=5.0)
            )

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

            # Check if model supports native tool calling
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
                    "ollama_using_prompt_tools",
                    model=self.model_name,
                    tools_count=len(tools),
                    reason="Model doesn't support native function calling, using prompt injection"
                )

            params.update(kwargs)

            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "started")

            response = await client.chat.completions.create(**params)

            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "success")

            # Parse response (OpenAI-compatible format)
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
                        "ollama_prompt_tools_parsed",
                        model=self.model_name,
                        tool_calls_found=len(tool_calls),
                        tool_names=[tc["name"] for tc in tool_calls]
                    )
                else:
                    # Model had tools available but didn't use them
                    has_tool_keywords = any(kw in content.lower() for kw in [
                        "switch", "model", "search", "remember", "send"
                    ])
                    logger.warning(
                        "ollama_prompt_tools_not_used",
                        model=self.model_name,
                        response_preview=content[:200] if content else "(empty)",
                        has_tool_keywords=has_tool_keywords,
                        hint="Model may have narrated action instead of calling tool"
                    )

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
                content=content,
                tool_calls=tool_calls,
                model=response.model,
                usage=usage,
                finish_reason=choice.finish_reason,
                raw_response=response
            )

        except Exception as e:
            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "error")
            logger.error("ollama_generation_failed", model=self.model_name, exc_info=True)

            # Classify error with helpful messages
            error_msg = str(e).lower()
            error_str = str(e)

            if "connection" in error_msg or "refused" in error_msg or "cannot connect" in error_msg:
                raise ModelNotAvailableError(
                    f"Cannot connect to Ollama. Make sure Ollama is running locally (ollama serve). "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "connection_failed"},
                    cause=e
                )
            elif "model" in error_msg and ("not found" in error_msg or "does not exist" in error_msg or "pull" in error_msg):
                # Auto-pull the model in background if we haven't tried yet
                if self.model_name not in _pull_attempted:
                    _pull_attempted.add(self.model_name)
                    logger.info("ollama_auto_pulling_model", model=self.model_name)
                    try:
                        import httpx
                        # Fire-and-forget: start the pull (streaming so it doesn't block)
                        # Ollama will download in the background
                        async with httpx.AsyncClient(timeout=10.0) as http_client:
                            await http_client.post(
                                "http://127.0.0.1:11434/api/pull",
                                json={"name": self.model_name, "stream": True},
                            )
                    except Exception:
                        pass  # Pull request sent, download continues in Ollama
                    raise ModelNotAvailableError(
                        f"Model '{self.model_name}' is being downloaded automatically. "
                        f"This is a one-time download (~5GB). Please wait a few minutes and try again.",
                        context={"model": self.model_name, "error_type": "model_pulling"},
                        cause=e
                    )
                raise ModelNotAvailableError(
                    f"Model '{self.model_name}' not found in Ollama. It may still be downloading. "
                    f"Run 'ollama pull {self.model_name}' to check status. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "model_not_found"},
                    cause=e
                )
            elif "timeout" in error_msg or "timed out" in error_msg:
                raise ModelAPIError(
                    f"Ollama request timed out. The model may be loading or your system may be under load. Try again. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "timeout"},
                    cause=e
                )
            elif "memory" in error_msg or "out of" in error_msg or "cuda" in error_msg:
                raise ModelAPIError(
                    f"Ollama ran out of memory. Try a smaller model or close other applications. "
                    f"Original error: {error_str}",
                    context={"model": self.model_name, "error_type": "out_of_memory"},
                    cause=e
                )
            else:
                raise ModelAPIError(
                    f"Ollama API error with model '{self.model_name}': {error_str}",
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
        """Stream response using Ollama API"""
        try:
            from openai import AsyncOpenAI
            import httpx

            # Timeout: 5s connect, 300s total for streaming (local reasoning models can be very slow)
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=httpx.Timeout(300.0, connect=5.0)
            )

            params = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Check if model supports native tool calling
            if tools and self.model_name not in self.TOOL_INCAPABLE_MODELS:
                params["tools"] = tools
                params["tool_choice"] = "auto"
            elif tools:
                # Use prompt-based tool calling for streaming too
                prompt_tool_handler = get_prompt_tool_handler()
                params["messages"] = prompt_tool_handler.inject_tools_into_messages(
                    messages, tools
                )
                logger.info(
                    "ollama_stream_using_prompt_tools",
                    model=self.model_name,
                    tools_count=len(tools),
                    reason="Model doesn't support native function calling, using prompt injection"
                )

            params.update(kwargs)

            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "started")

            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "success")

        except Exception as e:
            MetricsRecorder.record_ai_api_call("ollama", self.model_name, "error")
            logger.error("ollama_streaming_failed", model=self.model_name, exc_info=True)
            raise ModelAPIError(f"Ollama streaming error: {str(e)}", cause=e)

    def parse_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Parse tool calls from Ollama response (OpenAI format)"""
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
