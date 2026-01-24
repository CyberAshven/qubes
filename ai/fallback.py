"""
AI Fallback Chain

Implements multi-tier fallback for AI provider failures.
Matches documentation in docs/13_Implementation_Phases.md Phase 2

Fallback Strategy:
1. Primary model (user-configured, e.g., gpt-4o)
2. Secondary model (same provider, cheaper, e.g., gpt-4o-mini)
3. Tertiary model (different provider, e.g., claude-sonnet-4)
4. Sovereign mode (local Ollama, e.g., llama3.3:70b)
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ai.model_registry import ModelRegistry
from ai.providers.base import AIModelInterface, ModelResponse
from ai.circuit_breakers import CircuitBreakerRegistry
from core.exceptions import AIError, ModelAPIError
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FallbackModel:
    """
    Fallback model configuration

    Attributes:
        model_name: Model identifier (e.g., "gpt-4o", "claude-sonnet-4")
        priority: Priority level (1 = primary, 2 = secondary, etc.)
        reason: Why this model is in the chain
    """
    model_name: str
    priority: int
    reason: str


class AIFallbackChain:
    """
    Manages AI provider fallback chain

    If primary model fails, automatically tries backup models.
    Prevents total AI failure from single provider outage.
    """

    def __init__(
        self,
        primary_model: str,
        api_keys: Dict[str, str],
        enable_sovereign_fallback: bool = True
    ):
        """
        Initialize fallback chain

        Args:
            primary_model: Primary model to use (e.g., "gpt-4o")
            api_keys: API keys for all providers
            enable_sovereign_fallback: Enable Ollama fallback if all cloud models fail
        """
        self.primary_model = primary_model
        self.api_keys = api_keys
        self.enable_sovereign_fallback = enable_sovereign_fallback

        # Build fallback chain
        self.fallback_chain = self._build_fallback_chain()

        logger.info(
            "fallback_chain_initialized",
            primary_model=primary_model,
            chain_length=len(self.fallback_chain),
            sovereign_enabled=enable_sovereign_fallback
        )

    def _build_fallback_chain(self) -> List[FallbackModel]:
        """
        Build intelligent fallback chain based on primary model

        Strategy:
        1. Primary model (user choice)
        2. Cheaper model from same provider
        3. Equivalent model from different provider
        4. Local Ollama (if enabled)

        Returns:
            List of FallbackModel in priority order
        """
        chain = []

        # Get primary model info
        primary_info = ModelRegistry.get_model_info(self.primary_model)
        if not primary_info:
            raise AIError(
                f"Unknown primary model: {self.primary_model}",
                context={"model": self.primary_model}
            )

        primary_provider = primary_info["provider"]

        # 1. Primary model
        chain.append(FallbackModel(
            model_name=self.primary_model,
            priority=1,
            reason="Primary user-selected model"
        ))

        # 2. Secondary: Cheaper model from same provider
        secondary = self._get_cheaper_model(primary_provider)
        if secondary and secondary != self.primary_model:
            chain.append(FallbackModel(
                model_name=secondary,
                priority=2,
                reason=f"Cheaper fallback from {primary_provider}"
            ))

        # 3. Tertiary: Different provider
        tertiary = self._get_different_provider_model(primary_provider)
        if tertiary:
            chain.append(FallbackModel(
                model_name=tertiary,
                priority=3,
                reason="Cross-provider fallback"
            ))

        # 4. Sovereign mode (local Ollama)
        if self.enable_sovereign_fallback:
            sovereign = self._get_sovereign_model()
            if sovereign:
                chain.append(FallbackModel(
                    model_name=sovereign,
                    priority=4,
                    reason="Local sovereign fallback (offline-capable)"
                ))

        return chain

    def _get_cheaper_model(self, provider: str) -> Optional[str]:
        """
        Get cheaper model from same provider

        Args:
            provider: Provider name

        Returns:
            Model name or None
        """
        cheap_models = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3.5-haiku",
            "google": "gemini-2.5-flash-lite",
            "deepseek": "deepseek-chat",  # DeepSeek Chat is already the cheapest option
            "perplexity": "sonar"
        }

        return cheap_models.get(provider)

    def _get_different_provider_model(self, current_provider: str) -> Optional[str]:
        """
        Get equivalent model from different provider

        Args:
            current_provider: Current provider to avoid

        Returns:
            Model name from different provider or None
        """
        # Fallback preference order (by reliability)
        fallback_order = ["anthropic", "openai", "google", "deepseek", "perplexity"]

        # Remove current provider
        fallback_order = [p for p in fallback_order if p != current_provider]

        # Pick first available provider with API key
        for provider in fallback_order:
            if provider in self.api_keys:
                # Return good mid-tier model from that provider
                provider_models = {
                    "anthropic": "claude-sonnet-4-5-20250929",
                    "openai": "gpt-4o-mini",
                    "google": "gemini-2.5-flash",
                    "deepseek": "deepseek-chat",
                    "perplexity": "sonar"
                }
                return provider_models.get(provider)

        return None

    def _get_sovereign_model(self) -> Optional[str]:
        """
        Get best local Ollama model

        Returns:
            Ollama model name or None
        """
        # Priority order: largest model that fits most GPUs
        # llama3.3:70b requires ~48GB VRAM
        # qwen3:235b requires ~160GB VRAM (multi-GPU)
        # phi4:14b requires ~10GB VRAM (most accessible)

        return "llama3.3:70b"  # Best balance of quality and accessibility

    async def generate_with_fallback(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> tuple:
        """
        Generate response with automatic fallback on failure

        Tries each model in fallback chain until one succeeds.

        Args:
            messages: Conversation messages
            tools: Optional tool definitions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters

        Returns:
            Tuple of (ModelResponse, actual_model_name, actual_provider, fallback_occurred)

        Raises:
            AIError: If all models in chain fail
        """
        errors = []
        last_provider = None

        for fallback in self.fallback_chain:
            model_name = fallback.model_name
            provider_info = ModelRegistry.get_model_info(model_name)

            if not provider_info:
                logger.warning(
                    "fallback_model_not_found",
                    model=model_name,
                    reason=fallback.reason
                )
                continue

            provider = provider_info["provider"]

            # Check circuit breaker state
            if not CircuitBreakerRegistry.is_available(provider, model_name):
                logger.debug(
                    "fallback_model_circuit_open",
                    model=model_name,
                    provider=provider,
                    priority=fallback.priority
                )
                continue

            # Check if we have API key (skip if Ollama)
            if provider != "ollama" and provider not in self.api_keys:
                import sys
                print(f"DEBUG FALLBACK: No API key for provider={provider}, model={model_name}", file=sys.stderr)
                print(f"DEBUG FALLBACK: Available keys: {list(self.api_keys.keys())}", file=sys.stderr)
                logger.debug(
                    "fallback_model_no_api_key",
                    model=model_name,
                    provider=provider
                )
                continue

            # Clean context if provider changed - tool call formats are incompatible across providers
            current_messages = messages
            if last_provider is not None and last_provider != provider:
                logger.debug(
                    "fallback_cleaning_context_for_provider_switch",
                    from_provider=last_provider,
                    to_provider=provider
                )
                clean_messages = []
                for msg in messages:
                    role = msg.get("role")
                    if role == "system":
                        clean_messages.append(msg)
                    elif role == "user":
                        clean_messages.append({"role": "user", "content": msg.get("content", "")})
                    elif role == "assistant" and not msg.get("tool_calls"):
                        clean_messages.append({"role": "assistant", "content": msg.get("content", "")})
                    # Skip tool results and assistant messages with tool_calls
                current_messages = clean_messages

            # Track provider before attempting (so next iteration knows what we tried)
            last_provider = provider

            # Try this model
            try:
                import sys
                print(f"DEBUG FALLBACK: Attempting model={model_name}, provider={provider}, api_key={'***' if self.api_keys.get(provider) else 'NONE'}", file=sys.stderr)
                logger.debug(
                    "fallback_attempting_model",
                    model=model_name,
                    provider=provider,
                    priority=fallback.priority,
                    reason=fallback.reason
                )

                # Get model instance
                api_key = self.api_keys.get(provider) if provider != "ollama" else None
                model = ModelRegistry.get_model(model_name, api_key)

                # Generate response
                response = await model.generate(
                    messages=current_messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )

                # Only log INFO if we actually used fallback (not primary)
                fallback_occurred = fallback.priority > 1
                if fallback_occurred:
                    logger.info(
                        "fallback_model_success",
                        model=model_name,
                        provider=provider,
                        was_fallback=True
                    )
                else:
                    logger.debug("primary_model_success", model=model_name)

                return response, model_name, provider, fallback_occurred

            except Exception as e:
                import sys
                import traceback
                print(f"DEBUG FALLBACK: Model failed! model={model_name}, provider={provider}, error={str(e)}", file=sys.stderr)
                print(f"DEBUG FALLBACK: Traceback:\n{traceback.format_exc()}", file=sys.stderr)

                # Only log ERROR with traceback if this was the last fallback
                is_last = fallback == self.fallback_chain[-1]
                if is_last:
                    logger.error(
                        "fallback_model_failed",
                        model=model_name,
                        provider=provider,
                        priority=fallback.priority,
                        error=str(e),
                        exc_info=True
                    )
                else:
                    logger.debug(
                        "fallback_model_failed",
                        model=model_name,
                        provider=provider,
                        priority=fallback.priority,
                        error=str(e)
                    )

                errors.append({
                    "model": model_name,
                    "provider": provider,
                    "error": str(e)
                })

                # Continue to next model in chain
                continue

        # All models failed
        logger.error(
            "fallback_chain_exhausted",
            primary_model=self.primary_model,
            chain_length=len(self.fallback_chain),
            errors=errors
        )

        raise AIError(
            f"All models in fallback chain failed. Primary: {self.primary_model}",
            context={
                "primary_model": self.primary_model,
                "chain_length": len(self.fallback_chain),
                "errors": errors
            }
        )

    async def generate_primary_with_retry(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
        **kwargs
    ) -> tuple:
        """
        Generate response using ONLY the primary model with retries.

        This is for Manual mode where users explicitly choose their model
        and don't want silent fallback to different models.

        Args:
            messages: Conversation messages
            tools: Optional tool definitions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            max_retries: Number of retry attempts (default 3)
            **kwargs: Additional model-specific parameters

        Returns:
            Tuple of (ModelResponse, model_name, provider, False)

        Raises:
            AIError: If primary model fails after all retries
        """
        import asyncio

        model_name = self.primary_model
        provider_info = ModelRegistry.get_model_info(model_name)

        if not provider_info:
            raise AIError(
                f"Unknown model: {model_name}",
                context={"model": model_name}
            )

        provider = provider_info["provider"]

        # Check if we have API key (skip if Ollama)
        if provider != "ollama" and provider not in self.api_keys:
            raise AIError(
                f"API key not configured for {provider}",
                context={"model": model_name, "provider": provider}
            )

        # Get model instance
        api_key = self.api_keys.get(provider) if provider != "ollama" else None
        model = ModelRegistry.get_model(model_name, api_key)

        # Retry with exponential backoff
        retry_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s
        errors = []

        for attempt in range(max_retries):
            try:
                logger.debug(
                    "manual_mode_attempt",
                    model=model_name,
                    provider=provider,
                    attempt=attempt + 1,
                    max_retries=max_retries
                )

                response = await model.generate(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )

                logger.debug(
                    "manual_mode_success",
                    model=model_name,
                    provider=provider,
                    attempt=attempt + 1
                )

                # Return with fallback_occurred=False (we never fall back)
                return response, model_name, provider, False

            except Exception as e:
                error_str = str(e)
                errors.append({
                    "attempt": attempt + 1,
                    "error": error_str
                })

                # Check if this is a retryable error (5xx, timeout, rate limit)
                is_retryable = (
                    "500" in error_str or
                    "502" in error_str or
                    "503" in error_str or
                    "504" in error_str or
                    "timeout" in error_str.lower() or
                    "rate" in error_str.lower() or
                    "overloaded" in error_str.lower()
                )

                if attempt < max_retries - 1 and is_retryable:
                    delay = retry_delays[min(attempt, len(retry_delays) - 1)]
                    logger.warning(
                        "manual_mode_retrying",
                        model=model_name,
                        provider=provider,
                        attempt=attempt + 1,
                        delay=delay,
                        error=error_str
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Non-retryable error or exhausted retries
                    logger.error(
                        "manual_mode_failed",
                        model=model_name,
                        provider=provider,
                        attempt=attempt + 1,
                        error=error_str,
                        is_retryable=is_retryable,
                        exc_info=True
                    )
                    break

        # All retries exhausted - include the actual error in the message
        last_error = errors[-1]["error"] if errors else "Unknown error"
        actual_attempts = len(errors)
        raise AIError(
            f"Model '{model_name}' failed after {actual_attempts} attempt(s). "
            f"In Manual mode, no fallback to other models will occur.\n"
            f"Error: {last_error}",
            context={
                "model": model_name,
                "provider": provider,
                "attempts": actual_attempts,
                "errors": errors,
                "mode": "manual"
            }
        )

    def get_chain_info(self) -> List[Dict[str, Any]]:
        """
        Get information about fallback chain

        Returns:
            List of dicts with model info and availability
        """
        info = []

        for fallback in self.fallback_chain:
            model_info = ModelRegistry.get_model_info(fallback.model_name)
            provider = model_info["provider"] if model_info else "unknown"

            available = CircuitBreakerRegistry.is_available(provider, fallback.model_name)
            has_api_key = provider == "ollama" or provider in self.api_keys

            info.append({
                "model": fallback.model_name,
                "provider": provider,
                "priority": fallback.priority,
                "reason": fallback.reason,
                "available": available,
                "has_api_key": has_api_key,
                "usable": available and has_api_key
            })

        return info
