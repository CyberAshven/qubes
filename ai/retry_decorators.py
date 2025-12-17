"""
AI Retry Decorators with Tenacity

Implements exponential backoff with jitter for AI API calls.
Matches documentation in docs/13_Implementation_Phases.md Phase 2
"""

from typing import Optional, Type, Tuple
from functools import wraps
import asyncio
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from core.exceptions import (
    ModelAPIError,
    ModelRateLimitError,
    ModelNotAvailableError
)
from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# RETRY STRATEGIES
# =============================================================================

def ai_api_retry(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Retry decorator for AI API calls with exponential backoff + jitter

    Default behavior:
    - Retries on rate limits and transient API errors
    - Does NOT retry on authentication errors or model not found
    - Exponential backoff: 1s, 2s, 4s, 8s (with jitter)

    Args:
        max_attempts: Maximum retry attempts (default: 3)
        min_wait: Minimum wait time in seconds (default: 1)
        max_wait: Maximum wait time in seconds (default: 10)
        retry_on: Custom tuple of exceptions to retry on

    Example:
        @ai_api_retry(max_attempts=5)
        async def call_openai_api():
            # API call here
            pass
    """
    if retry_on is None:
        # Default: retry on rate limits and generic API errors
        # Do NOT retry on authentication or model not found
        retry_on = (ModelAPIError, ModelRateLimitError)

    def decorator(func):
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=min_wait,
                min=min_wait,
                max=max_wait
            ),
            retry=retry_if_exception_type(retry_on),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO)
        )
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=min_wait,
                min=min_wait,
                max=max_wait
            ),
            retry=retry_if_exception_type(retry_on),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO)
        )
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def ai_api_retry_aggressive(
    max_attempts: int = 5,
    min_wait: int = 2,
    max_wait: int = 30
):
    """
    Aggressive retry strategy for critical AI operations

    Use this for operations that MUST succeed (e.g., reasoning loop)
    - More retry attempts (5 vs 3)
    - Longer backoff (up to 30s)

    Example:
        @ai_api_retry_aggressive()
        async def critical_reasoning_step():
            # Critical operation
            pass
    """
    return ai_api_retry(
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait
    )


def ai_api_retry_conservative(
    max_attempts: int = 2,
    min_wait: int = 1,
    max_wait: int = 5
):
    """
    Conservative retry strategy for non-critical operations

    Use this for operations that can fail gracefully (e.g., optional tools)
    - Fewer retry attempts (2 vs 3)
    - Shorter backoff (up to 5s)

    Example:
        @ai_api_retry_conservative()
        async def optional_image_generation():
            # Non-critical operation
            pass
    """
    return ai_api_retry(
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait
    )


# =============================================================================
# PROVIDER-SPECIFIC RETRY STRATEGIES
# =============================================================================

def openai_retry(max_attempts: int = 3):
    """
    Retry strategy specific to OpenAI API

    Handles OpenAI-specific errors:
    - Rate limits (429)
    - Server errors (500, 502, 503, 504)
    - Timeout errors

    Does NOT retry:
    - Authentication errors (401)
    - Model not found (404)
    - Invalid requests (400)
    """
    return ai_api_retry(
        max_attempts=max_attempts,
        min_wait=1,
        max_wait=10,
        retry_on=(ModelAPIError, ModelRateLimitError)
    )


def anthropic_retry(max_attempts: int = 3):
    """
    Retry strategy specific to Anthropic API

    Anthropic has generous rate limits but slower response times
    Use slightly longer backoff
    """
    return ai_api_retry(
        max_attempts=max_attempts,
        min_wait=2,
        max_wait=15,
        retry_on=(ModelAPIError, ModelRateLimitError)
    )


def google_retry(max_attempts: int = 3):
    """
    Retry strategy specific to Google Gemini API

    Google APIs have quota limits that reset daily
    """
    return ai_api_retry(
        max_attempts=max_attempts,
        min_wait=1,
        max_wait=10,
        retry_on=(ModelAPIError, ModelRateLimitError)
    )


def perplexity_retry(max_attempts: int = 3):
    """
    Retry strategy specific to Perplexity API

    Perplexity uses OpenAI-compatible API
    """
    return ai_api_retry(
        max_attempts=max_attempts,
        min_wait=1,
        max_wait=10,
        retry_on=(ModelAPIError, ModelRateLimitError)
    )


def ollama_retry(max_attempts: int = 2):
    """
    Retry strategy for local Ollama models

    Local models fail fast and should not retry aggressively
    Only retry on true errors, not on model availability
    """
    return ai_api_retry(
        max_attempts=max_attempts,
        min_wait=1,
        max_wait=5,
        retry_on=(ModelAPIError,)  # No rate limits for local
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def should_retry_error(error: Exception) -> bool:
    """
    Determine if an error should be retried

    Args:
        error: Exception to check

    Returns:
        True if error is retryable, False otherwise
    """
    # Never retry model not available errors
    if isinstance(error, ModelNotAvailableError):
        return False

    # Retry rate limits
    if isinstance(error, ModelRateLimitError):
        return True

    # Retry generic API errors (server issues, timeouts, etc.)
    if isinstance(error, ModelAPIError):
        return True

    # Don't retry unknown errors
    return False


def get_retry_strategy_for_provider(provider: str):
    """
    Get appropriate retry decorator for a provider

    Args:
        provider: Provider name ("openai", "anthropic", etc.)

    Returns:
        Retry decorator function
    """
    strategies = {
        "openai": openai_retry,
        "anthropic": anthropic_retry,
        "google": google_retry,
        "perplexity": perplexity_retry,
        "ollama": ollama_retry
    }

    return strategies.get(provider, ai_api_retry)
