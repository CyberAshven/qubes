"""
Tests for AI Retry Decorators

Comprehensive tests for exponential backoff retry logic with Tenacity.
Validates retry behavior for different error types, configurations, and providers.

Covers:
- Basic retry behavior (success after retries)
- Retry on specific exceptions
- Non-retryable exceptions
- Max attempts enforcement
- Exponential backoff timing
- Async vs sync function handling
- Provider-specific retry strategies
- Helper function behavior
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from tenacity import RetryError

from ai.retry_decorators import (
    ai_api_retry,
    ai_api_retry_aggressive,
    ai_api_retry_conservative,
    openai_retry,
    anthropic_retry,
    google_retry,
    perplexity_retry,
    ollama_retry,
    should_retry_error,
    get_retry_strategy_for_provider
)

from core.exceptions import (
    ModelAPIError,
    ModelRateLimitError,
    ModelNotAvailableError
)


# ==============================================================================
# BASIC RETRY BEHAVIOR TESTS
# ==============================================================================

class TestBasicRetry:
    """Test basic retry decorator functionality"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Should succeed after initial failures"""
        call_count = {"value": 0}

        @ai_api_retry(max_attempts=3)
        async def flaky_function():
            call_count["value"] += 1
            if call_count["value"] < 3:
                raise ModelAPIError("Temporary error")
            return "success"

        result = await flaky_function()

        assert result == "success"
        assert call_count["value"] == 3  # Failed twice, succeeded third time

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_fails_after_max_attempts(self):
        """Should raise exception after exhausting retries"""

        @ai_api_retry(max_attempts=3)
        async def always_fails():
            raise ModelAPIError("Permanent error")

        # Tenacity raises RetryError when all attempts exhausted
        with pytest.raises(RetryError):
            await always_fails()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_immediate_success_no_retry(self):
        """Should succeed immediately without retries"""
        call_count = {"value": 0}

        @ai_api_retry(max_attempts=3)
        async def successful_function():
            call_count["value"] += 1
            return "success"

        result = await successful_function()

        assert result == "success"
        assert call_count["value"] == 1  # Only called once

    @pytest.mark.unit
    def test_sync_function_retry(self):
        """Should work with synchronous functions"""
        call_count = {"value": 0}

        @ai_api_retry(max_attempts=3)
        def flaky_sync_function():
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise ModelAPIError("Temporary error")
            return "success"

        result = flaky_sync_function()

        assert result == "success"
        assert call_count["value"] == 2


# ==============================================================================
# EXCEPTION HANDLING TESTS
# ==============================================================================

class TestExceptionHandling:
    """Test retry behavior for different exception types"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit_error(self):
        """Should retry on ModelRateLimitError"""
        call_count = {"value": 0}

        @ai_api_retry(max_attempts=3)
        async def rate_limited():
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise ModelRateLimitError("Rate limit exceeded")
            return "success"

        result = await rate_limited()

        assert result == "success"
        assert call_count["value"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_retry_on_model_not_available(self):
        """Should NOT retry on ModelNotAvailableError"""
        call_count = {"value": 0}

        @ai_api_retry(max_attempts=3, retry_on=(ModelAPIError, ModelRateLimitError))
        async def model_not_available():
            call_count["value"] += 1
            raise ModelNotAvailableError("Model not found")

        with pytest.raises(ModelNotAvailableError):
            await model_not_available()

        # Should fail immediately without retries
        assert call_count["value"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_custom_retry_exceptions(self):
        """Should retry only on specified exceptions"""
        call_count = {"value": 0}

        @ai_api_retry(max_attempts=3, retry_on=(ModelRateLimitError,))
        async def custom_retry():
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise ModelRateLimitError("Rate limit")
            return "success"

        result = await custom_retry()
        assert result == "success"

        # Reset and test non-retryable exception
        call_count["value"] = 0

        @ai_api_retry(max_attempts=3, retry_on=(ModelRateLimitError,))
        async def non_retryable():
            call_count["value"] += 1
            raise ModelAPIError("API Error")

        with pytest.raises(ModelAPIError):
            await non_retryable()

        # Should fail immediately (ModelAPIError not in retry_on)
        assert call_count["value"] == 1


# ==============================================================================
# RETRY STRATEGY TESTS
# ==============================================================================

class TestRetryStrategies:
    """Test different retry strategy configurations"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_aggressive_strategy_more_retries(self):
        """Aggressive strategy should allow more retry attempts"""
        call_count = {"value": 0}

        @ai_api_retry_aggressive()
        async def flaky_critical():
            call_count["value"] += 1
            if call_count["value"] < 5:
                raise ModelAPIError("Error")
            return "success"

        result = await flaky_critical()

        assert result == "success"
        assert call_count["value"] == 5  # Used all 5 aggressive attempts

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_conservative_strategy_fewer_retries(self):
        """Conservative strategy should fail faster"""
        call_count = {"value": 0}

        @ai_api_retry_conservative()
        async def flaky_optional():
            call_count["value"] += 1
            raise ModelAPIError("Error")

        with pytest.raises(RetryError):
            await flaky_optional()

        # Conservative only tries 2 times
        assert call_count["value"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_custom_max_attempts(self):
        """Should respect custom max_attempts parameter"""
        call_count = {"value": 0}

        @ai_api_retry(max_attempts=5)
        async def custom_retries():
            call_count["value"] += 1
            raise ModelAPIError("Error")

        with pytest.raises(RetryError):
            await custom_retries()

        assert call_count["value"] == 5


# ==============================================================================
# PROVIDER-SPECIFIC RETRY TESTS
# ==============================================================================

class TestProviderRetries:
    """Test provider-specific retry configurations"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_openai_retry_configuration(self):
        """OpenAI retry should use standard config"""
        call_count = {"value": 0}

        @openai_retry()
        async def openai_call():
            call_count["value"] += 1
            raise ModelAPIError("Error")

        with pytest.raises(RetryError):
            await openai_call()

        assert call_count["value"] == 3  # Standard 3 attempts

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_anthropic_retry_configuration(self):
        """Anthropic retry should use longer backoff"""
        call_count = {"value": 0}

        @anthropic_retry()
        async def anthropic_call():
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise ModelRateLimitError("Rate limit")
            return "success"

        result = await anthropic_call()

        assert result == "success"
        assert call_count["value"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ollama_retry_no_rate_limit(self):
        """Ollama retry should NOT retry on rate limits (local model)"""
        call_count = {"value": 0}

        @ollama_retry()
        async def ollama_call():
            call_count["value"] += 1
            raise ModelRateLimitError("Rate limit")

        # Ollama doesn't retry on rate limits (local models don't have them)
        with pytest.raises(ModelRateLimitError):
            await ollama_call()

        assert call_count["value"] == 1  # No retry

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ollama_retry_on_api_error(self):
        """Ollama should retry on generic API errors"""
        call_count = {"value": 0}

        @ollama_retry()
        async def ollama_call():
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise ModelAPIError("Connection error")
            return "success"

        result = await ollama_call()

        assert result == "success"
        assert call_count["value"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_google_retry_configuration(self):
        """Google retry should use standard config"""
        call_count = {"value": 0}

        @google_retry()
        async def google_call():
            call_count["value"] += 1
            raise ModelAPIError("Error")

        with pytest.raises(RetryError):
            await google_call()

        assert call_count["value"] == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_perplexity_retry_configuration(self):
        """Perplexity retry should use standard config"""
        call_count = {"value": 0}

        @perplexity_retry()
        async def perplexity_call():
            call_count["value"] += 1
            raise ModelAPIError("Error")

        with pytest.raises(RetryError):
            await perplexity_call()

        assert call_count["value"] == 3


# ==============================================================================
# HELPER FUNCTION TESTS
# ==============================================================================

class TestHelperFunctions:
    """Test retry helper functions"""

    @pytest.mark.unit
    def test_should_retry_rate_limit(self):
        """Rate limit errors should be retryable"""
        error = ModelRateLimitError("Rate limit exceeded")
        assert should_retry_error(error) is True

    @pytest.mark.unit
    def test_should_retry_api_error(self):
        """Generic API errors should be retryable"""
        error = ModelAPIError("Server error")
        assert should_retry_error(error) is True

    @pytest.mark.unit
    def test_should_not_retry_model_not_available(self):
        """Model not available errors should NOT be retryable"""
        error = ModelNotAvailableError("Model not found")
        assert should_retry_error(error) is False

    @pytest.mark.unit
    def test_should_not_retry_unknown_error(self):
        """Unknown errors should NOT be retryable"""
        error = ValueError("Unknown error")
        assert should_retry_error(error) is False

    @pytest.mark.unit
    def test_get_retry_strategy_for_provider(self):
        """Should return correct retry strategy for each provider"""
        assert get_retry_strategy_for_provider("openai") == openai_retry
        assert get_retry_strategy_for_provider("anthropic") == anthropic_retry
        assert get_retry_strategy_for_provider("google") == google_retry
        assert get_retry_strategy_for_provider("perplexity") == perplexity_retry
        assert get_retry_strategy_for_provider("ollama") == ollama_retry

    @pytest.mark.unit
    def test_get_retry_strategy_unknown_provider(self):
        """Should return default strategy for unknown provider"""
        strategy = get_retry_strategy_for_provider("unknown_provider")
        assert strategy == ai_api_retry


# ==============================================================================
# TIMING & BACKOFF TESTS
# ==============================================================================

class TestBackoffTiming:
    """Test exponential backoff timing behavior"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exponential_backoff_occurs(self):
        """Should wait between retry attempts"""
        call_times = []

        @ai_api_retry(max_attempts=3, min_wait=0.1, max_wait=1)
        async def timed_failures():
            call_times.append(time.time())
            raise ModelAPIError("Error")

        with pytest.raises(RetryError):
            await timed_failures()

        # Should have 3 calls
        assert len(call_times) == 3

        # Check that there was a delay between attempts
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # First delay should be at least min_wait (0.1s)
        assert delay1 >= 0.1
        # Second delay should be longer (exponential backoff)
        assert delay2 >= delay1 * 0.9  # Allow some jitter tolerance

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wait_time_respects_max_wait(self):
        """Wait time should not exceed max_wait"""
        call_times = []

        @ai_api_retry(max_attempts=5, min_wait=1, max_wait=2)
        async def max_wait_test():
            call_times.append(time.time())
            raise ModelAPIError("Error")

        with pytest.raises(RetryError):
            await max_wait_test()

        # Check that no delay exceeds max_wait
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i-1]
            assert delay <= 3  # max_wait (2s) + some tolerance


# ==============================================================================
# EDGE CASES & INTEGRATION TESTS
# ==============================================================================

class TestEdgeCases:
    """Test edge cases and complex scenarios"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_with_return_value(self):
        """Should preserve return values through retries"""
        call_count = {"value": 0}

        @ai_api_retry(max_attempts=3)
        async def returns_data():
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise ModelAPIError("Error")
            return {"data": "important", "count": call_count["value"]}

        result = await returns_data()

        assert result["data"] == "important"
        assert result["count"] == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_with_function_args(self):
        """Should preserve function arguments through retries"""
        call_count = {"value": 0}

        @ai_api_retry(max_attempts=3)
        async def function_with_args(arg1, arg2, kwarg1=None):
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise ModelAPIError("Error")
            return f"{arg1}-{arg2}-{kwarg1}"

        result = await function_with_args("a", "b", kwarg1="c")

        assert result == "a-b-c"
        assert call_count["value"] == 2

    @pytest.mark.unit
    def test_sync_and_async_same_decorator(self):
        """Decorator should handle both sync and async functions"""
        async_count = {"value": 0}
        sync_count = {"value": 0}

        @ai_api_retry(max_attempts=2)
        async def async_func():
            async_count["value"] += 1
            if async_count["value"] < 2:
                raise ModelAPIError("Error")
            return "async_success"

        @ai_api_retry(max_attempts=2)
        def sync_func():
            sync_count["value"] += 1
            if sync_count["value"] < 2:
                raise ModelAPIError("Error")
            return "sync_success"

        # Test async
        result_async = asyncio.run(async_func())
        assert result_async == "async_success"
        assert async_count["value"] == 2

        # Test sync
        result_sync = sync_func()
        assert result_sync == "sync_success"
        assert sync_count["value"] == 2
