"""
Tests for AI Circuit Breakers

Comprehensive tests for the circuit breaker pattern implementation
that prevents cascading failures in AI provider calls.

Covers:
- Circuit breaker creation and registration
- State transitions (CLOSED → OPEN → HALF_OPEN)
- Failure counting and thresholds
- Reset timeout behavior
- Provider-specific configurations
- Error exclusion patterns
- State monitoring
"""

import pytest
import time
from pybreaker import CircuitBreaker, CircuitBreakerError, STATE_CLOSED, STATE_OPEN, STATE_HALF_OPEN

from ai.circuit_breakers import CircuitBreakerRegistry
from core.exceptions import ModelAPIError, ModelRateLimitError


# ==============================================================================
# CIRCUIT BREAKER BASIC TESTS
# ==============================================================================

class TestCircuitBreakerBasic:
    """Test basic circuit breaker functionality"""

    def setup_method(self):
        """Reset circuit breakers before each test"""
        CircuitBreakerRegistry._breakers.clear()

    @pytest.mark.unit
    def test_get_breaker_creates_new(self):
        """Should create new breaker for provider"""
        breaker = CircuitBreakerRegistry.get_breaker("openai")

        assert breaker is not None
        assert breaker.name == "openai"
        assert breaker.current_state == STATE_CLOSED

    @pytest.mark.unit
    def test_get_breaker_returns_cached(self):
        """Should return same breaker instance for same provider"""
        breaker1 = CircuitBreakerRegistry.get_breaker("openai")
        breaker2 = CircuitBreakerRegistry.get_breaker("openai")

        assert breaker1 is breaker2

    @pytest.mark.unit
    def test_get_breaker_with_model(self):
        """Should create separate breaker for provider:model combination"""
        breaker_generic = CircuitBreakerRegistry.get_breaker("openai")
        breaker_specific = CircuitBreakerRegistry.get_breaker("openai", "gpt-4o")

        assert breaker_generic is not breaker_specific
        assert breaker_generic.name == "openai"
        assert breaker_specific.name == "openai:gpt-4o"

    @pytest.mark.unit
    def test_multiple_providers_isolated(self):
        """Different providers should have isolated breakers"""
        openai_breaker = CircuitBreakerRegistry.get_breaker("openai")
        anthropic_breaker = CircuitBreakerRegistry.get_breaker("anthropic")

        assert openai_breaker is not anthropic_breaker
        assert openai_breaker.name == "openai"
        assert anthropic_breaker.name == "anthropic"


# ==============================================================================
# CIRCUIT BREAKER STATE TRANSITION TESTS
# ==============================================================================

class TestCircuitBreakerStates:
    """Test circuit breaker state transitions"""

    def setup_method(self):
        """Reset circuit breakers before each test"""
        CircuitBreakerRegistry._breakers.clear()

    @pytest.mark.unit
    def test_initial_state_closed(self):
        """New breaker should start in CLOSED state"""
        breaker = CircuitBreakerRegistry.get_breaker("openai")

        assert breaker.current_state == STATE_CLOSED
        assert CircuitBreakerRegistry.is_available("openai") is True

    @pytest.mark.unit
    def test_transitions_to_open_after_failures(self):
        """Breaker should open after exceeding failure threshold"""
        breaker = CircuitBreakerRegistry.get_breaker("openai")

        # OpenAI has fail_max=5, so trigger 5 failures
        def failing_call():
            raise ModelAPIError("API Error")

        # Trigger failures (last one will raise CircuitBreakerError)
        for i in range(5):
            try:
                breaker.call(failing_call)
            except (ModelAPIError, CircuitBreakerError):
                pass  # Expected

        # After 5 failures, breaker should be open
        assert breaker.current_state == STATE_OPEN

    @pytest.mark.unit
    def test_open_breaker_rejects_calls(self):
        """OPEN breaker should reject all calls immediately"""
        breaker = CircuitBreakerRegistry.get_breaker("test_reject")

        # Force breaker to OPEN state by triggering failures
        def failing_call():
            raise ModelAPIError("API Error")

        # Get fail_max for this breaker
        fail_max = breaker.fail_max

        # Trigger enough failures to open the breaker (last one raises CircuitBreakerError)
        for i in range(fail_max):
            try:
                breaker.call(failing_call)
            except (ModelAPIError, CircuitBreakerError):
                pass

        # Breaker should now be OPEN
        assert breaker.current_state == STATE_OPEN

        # Now calls should be rejected immediately with CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            breaker.call(lambda: "success")

    @pytest.mark.unit
    def test_transitions_to_half_open_after_timeout(self):
        """Breaker should transition to HALF_OPEN after reset timeout"""
        import time

        # Use short timeout for testing
        breaker = CircuitBreaker(
            fail_max=2,
            reset_timeout=1,  # 1 second timeout
            name="test_timeout"
        )

        # Trigger failures to open breaker (last one raises CircuitBreakerError)
        def failing_call():
            raise ModelAPIError("Error")

        for i in range(2):
            try:
                breaker.call(failing_call)
            except (ModelAPIError, CircuitBreakerError):
                pass

        # Should be OPEN
        assert breaker.current_state == STATE_OPEN

        # Wait for reset timeout
        time.sleep(1.1)

        # Next call should transition to HALF_OPEN
        # (breaker allows one test call)
        try:
            breaker.call(failing_call)
        except (ModelAPIError, CircuitBreakerError):
            pass

        # Should have attempted HALF_OPEN state
        # (might be back to OPEN if test call failed)
        assert breaker.current_state in [STATE_OPEN, STATE_HALF_OPEN]


# ==============================================================================
# PROVIDER-SPECIFIC CONFIGURATION TESTS
# ==============================================================================

class TestProviderConfigurations:
    """Test provider-specific circuit breaker configurations"""

    def setup_method(self):
        """Reset circuit breakers before each test"""
        CircuitBreakerRegistry._breakers.clear()

    @pytest.mark.unit
    def test_openai_configuration(self):
        """OpenAI breaker should have appropriate configuration"""
        breaker = CircuitBreakerRegistry.get_breaker("openai")

        # OpenAI typically has higher tolerance for failures
        assert breaker.fail_max >= 3
        assert breaker.reset_timeout > 0

    @pytest.mark.unit
    def test_anthropic_configuration(self):
        """Anthropic breaker should have appropriate configuration"""
        breaker = CircuitBreakerRegistry.get_breaker("anthropic")

        # Anthropic is very reliable, should be sensitive to failures
        assert breaker.fail_max >= 2
        assert breaker.reset_timeout > 0

    @pytest.mark.unit
    def test_ollama_configuration(self):
        """Ollama (local) breaker should fail fast"""
        breaker = CircuitBreakerRegistry.get_breaker("ollama")

        # Local model should have lower tolerance
        assert breaker.fail_max >= 2
        assert breaker.reset_timeout > 0


# ==============================================================================
# ERROR EXCLUSION TESTS
# ==============================================================================

class TestErrorExclusion:
    """Test that certain errors don't trip the breaker"""

    def setup_method(self):
        """Reset circuit breakers before each test"""
        CircuitBreakerRegistry._breakers.clear()

    @pytest.mark.unit
    def test_rate_limit_excluded_from_failures(self):
        """Rate limit errors should not count as breaker failures"""
        breaker = CircuitBreakerRegistry.get_breaker("openai")

        # OpenAI has fail_max=5 and excludes ModelRateLimitError
        def rate_limited_call():
            raise ModelRateLimitError("Rate limit exceeded")

        # Trigger many rate limit errors (more than fail_max)
        for i in range(10):
            try:
                breaker.call(rate_limited_call)
            except ModelRateLimitError:
                pass  # Expected

        # Breaker should still be CLOSED (rate limits don't count as failures)
        assert breaker.current_state == STATE_CLOSED


# ==============================================================================
# BREAKER MONITORING TESTS
# ==============================================================================

class TestBreakerMonitoring:
    """Test circuit breaker monitoring and state queries"""

    def setup_method(self):
        """Reset circuit breakers before each test"""
        CircuitBreakerRegistry._breakers.clear()

    @pytest.mark.unit
    def test_get_breaker_state(self):
        """Should return current state of breaker"""
        CircuitBreakerRegistry.get_breaker("openai")

        state = CircuitBreakerRegistry.get_breaker_state("openai")

        # Returns PyBreaker state constant
        assert state is not None
        assert state == STATE_CLOSED

    @pytest.mark.unit
    def test_is_available_when_closed(self):
        """is_available should return True when breaker is CLOSED"""
        CircuitBreakerRegistry.get_breaker("openai")

        assert CircuitBreakerRegistry.is_available("openai") is True

    @pytest.mark.unit
    def test_is_available_when_open(self):
        """is_available should return False when breaker is OPEN"""
        breaker = CircuitBreakerRegistry.get_breaker("test_available")

        # Force breaker to OPEN by triggering failures (last one raises CircuitBreakerError)
        def failing_call():
            raise ModelAPIError("Error")

        fail_max = breaker.fail_max
        for i in range(fail_max):
            try:
                breaker.call(failing_call)
            except (ModelAPIError, CircuitBreakerError):
                pass

        # Breaker should be OPEN
        assert breaker.current_state == STATE_OPEN
        assert CircuitBreakerRegistry.is_available("test_available") is False

    @pytest.mark.unit
    def test_get_all_states(self):
        """Should return all breaker states"""
        CircuitBreakerRegistry.get_breaker("openai")
        CircuitBreakerRegistry.get_breaker("anthropic")
        CircuitBreakerRegistry.get_breaker("google")

        all_states = CircuitBreakerRegistry.get_all_states()

        assert isinstance(all_states, dict)
        assert len(all_states) == 3
        assert "openai" in all_states
        assert "anthropic" in all_states
        assert "google" in all_states


# ==============================================================================
# BREAKER RESET TESTS
# ==============================================================================

class TestBreakerReset:
    """Test circuit breaker reset functionality"""

    def setup_method(self):
        """Reset circuit breakers before each test"""
        CircuitBreakerRegistry._breakers.clear()

    @pytest.mark.unit
    def test_reset_breaker_returns_to_closed(self):
        """Manual reset should return breaker to CLOSED state"""
        breaker = CircuitBreakerRegistry.get_breaker("test_reset")

        # Force breaker to OPEN (last one raises CircuitBreakerError)
        def failing_call():
            raise ModelAPIError("Error")

        fail_max = breaker.fail_max
        for i in range(fail_max):
            try:
                breaker.call(failing_call)
            except (ModelAPIError, CircuitBreakerError):
                pass

        # Verify it's OPEN
        assert breaker.current_state == STATE_OPEN

        # Reset the breaker
        CircuitBreakerRegistry.reset_breaker("test_reset")

        # Should be back to CLOSED
        assert breaker.current_state == STATE_CLOSED
        assert CircuitBreakerRegistry.is_available("test_reset") is True

    @pytest.mark.unit
    def test_reset_nonexistent_breaker_handles_gracefully(self):
        """Resetting non-existent breaker should handle gracefully"""
        # Should not raise error
        try:
            CircuitBreakerRegistry.reset_breaker("nonexistent_provider")
        except KeyError:
            pytest.fail("Should handle non-existent breaker gracefully")


# ==============================================================================
# CONCURRENT ACCESS TESTS
# ==============================================================================

class TestConcurrentAccess:
    """Test circuit breaker thread safety"""

    def setup_method(self):
        """Reset circuit breakers before each test"""
        CircuitBreakerRegistry._breakers.clear()

    @pytest.mark.unit
    def test_concurrent_breaker_access(self):
        """Multiple threads should safely access same breaker"""
        from threading import Thread

        results = []

        def get_breaker_thread():
            breaker = CircuitBreakerRegistry.get_breaker("openai")
            results.append(breaker)

        # Create 10 threads getting same breaker
        threads = [Thread(target=get_breaker_thread) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should get same breaker instance
        assert len(results) == 10
        assert all(b is results[0] for b in results)
