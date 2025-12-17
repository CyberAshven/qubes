"""
AI Circuit Breakers with PyBreaker

Implements circuit breaker pattern to prevent cascading failures.
Matches documentation in docs/13_Implementation_Phases.md Phase 2
"""

from typing import Dict, Optional
from pybreaker import CircuitBreaker, CircuitBreakerError
from datetime import timedelta

from core.exceptions import ModelAPIError, ModelRateLimitError
from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# CIRCUIT BREAKER LISTENER
# =============================================================================

class CircuitBreakerListener:
    """
    Listener for circuit breaker state changes

    Implements PyBreaker's listener protocol to log state transitions
    """

    def state_change(self, breaker, old_state, new_state):
        """Called when circuit breaker changes state"""
        logger.info(
            "circuit_breaker_state_change",
            breaker_name=breaker.name,
            old_state=old_state.name,
            new_state=new_state.name
        )

        # Log specific transitions
        if new_state.name == 'open':
            logger.error(
                "circuit_breaker_opened",
                breaker_name=breaker.name,
                failure_count=breaker.fail_counter
            )
        elif new_state.name == 'closed':
            logger.info(
                "circuit_breaker_closed",
                breaker_name=breaker.name
            )
        elif new_state.name == 'half_open':
            logger.warning(
                "circuit_breaker_half_open",
                breaker_name=breaker.name
            )

    def before_call(self, breaker, func, *args, **kwargs):
        """Called before attempting a call through the breaker"""
        pass

    def failure(self, breaker, exception):
        """Called when a call fails"""
        logger.warning(
            "circuit_breaker_failure",
            breaker_name=breaker.name,
            exception=str(exception),
            failure_count=breaker.fail_counter
        )

    def success(self, breaker):
        """Called when a call succeeds"""
        pass


# =============================================================================
# CIRCUIT BREAKER REGISTRY
# =============================================================================

class CircuitBreakerRegistry:
    """
    Global registry of circuit breakers for AI providers

    Each provider gets its own circuit breaker to prevent one failing
    provider from affecting others.
    """

    _breakers: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_breaker(cls, provider: str, model: Optional[str] = None) -> CircuitBreaker:
        """
        Get or create circuit breaker for a provider/model

        Args:
            provider: Provider name ("openai", "anthropic", etc.)
            model: Optional specific model name for finer-grained breakers

        Returns:
            CircuitBreaker instance
        """
        # Create unique key for this breaker
        key = f"{provider}:{model}" if model else provider

        if key not in cls._breakers:
            cls._breakers[key] = cls._create_breaker(provider, model)
            logger.info(
                "circuit_breaker_created",
                provider=provider,
                model=model,
                key=key
            )

        return cls._breakers[key]

    @classmethod
    def _create_breaker(cls, provider: str, model: Optional[str] = None) -> CircuitBreaker:
        """
        Create circuit breaker with provider-specific configuration

        Circuit Breaker States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Too many failures, reject all requests immediately
        - HALF_OPEN: Testing if service recovered, allow 1 request

        Args:
            provider: Provider name
            model: Optional model name

        Returns:
            Configured CircuitBreaker
        """
        # Get provider-specific configuration
        config = cls._get_provider_config(provider)

        breaker = CircuitBreaker(
            fail_max=config["fail_max"],
            reset_timeout=config["reset_timeout"],
            exclude=config["exclude"],
            name=f"{provider}:{model}" if model else provider,
            listeners=[CircuitBreakerListener()]
        )

        return breaker

    @classmethod
    def _get_provider_config(cls, provider: str) -> dict:
        """
        Get circuit breaker configuration for provider

        Different providers have different reliability characteristics:
        - OpenAI: High volume, occasional rate limits
        - Anthropic: Very reliable, rare failures
        - Google: Good reliability, quota-based limits
        - Perplexity: Medium reliability
        - Ollama: Local, should fail fast

        Returns:
            Configuration dict with fail_max, reset_timeout, exclude
        """
        configs = {
            "openai": {
                "fail_max": 5,  # Open after 5 failures
                "reset_timeout": 60,  # Try again after 60 seconds
                "exclude": [ModelRateLimitError]  # Don't count rate limits as failures
            },
            "anthropic": {
                "fail_max": 3,  # Open after 3 failures (rare, so stricter)
                "reset_timeout": 120,  # Wait 2 minutes before retry
                "exclude": [ModelRateLimitError]
            },
            "google": {
                "fail_max": 5,
                "reset_timeout": 60,
                "exclude": [ModelRateLimitError]
            },
            "perplexity": {
                "fail_max": 4,
                "reset_timeout": 90,
                "exclude": [ModelRateLimitError]
            },
            "ollama": {
                "fail_max": 2,  # Fail fast for local models
                "reset_timeout": 30,  # Quick recovery
                "exclude": []  # Count all errors
            }
        }

        # Default configuration for unknown providers
        default = {
            "fail_max": 5,
            "reset_timeout": 60,
            "exclude": [ModelRateLimitError]
        }

        return configs.get(provider, default)

    @classmethod
    def reset_breaker(cls, provider: str, model: Optional[str] = None):
        """
        Manually reset a circuit breaker

        Args:
            provider: Provider name
            model: Optional model name
        """
        key = f"{provider}:{model}" if model else provider

        if key in cls._breakers:
            cls._breakers[key].close()
            logger.info("circuit_breaker_manually_reset", key=key)

    @classmethod
    def get_breaker_state(cls, provider: str, model: Optional[str] = None) -> str:
        """
        Get current state of a circuit breaker

        Args:
            provider: Provider name
            model: Optional model name

        Returns:
            State string: "closed", "open", or "half_open"
        """
        breaker = cls.get_breaker(provider, model)
        return breaker.current_state

    @classmethod
    def is_available(cls, provider: str, model: Optional[str] = None) -> bool:
        """
        Check if a provider/model is currently available

        Args:
            provider: Provider name
            model: Optional model name

        Returns:
            True if breaker is closed (service available), False otherwise
        """
        state = cls.get_breaker_state(provider, model)
        return state == "closed"

    @classmethod
    def get_all_states(cls) -> Dict[str, str]:
        """
        Get states of all circuit breakers

        Returns:
            Dict mapping breaker name to state
        """
        return {
            name: breaker.current_state
            for name, breaker in cls._breakers.items()
        }


# =============================================================================
# CIRCUIT BREAKER DECORATORS
# =============================================================================

def with_circuit_breaker(provider: str, model: Optional[str] = None):
    """
    Decorator to protect AI API calls with circuit breaker

    If circuit is OPEN (too many failures), raises CircuitBreakerError
    immediately without calling the API.

    Args:
        provider: Provider name
        model: Optional model name

    Example:
        @with_circuit_breaker("openai", "gpt-4o")
        async def call_openai():
            # API call here
            pass
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            breaker = CircuitBreakerRegistry.get_breaker(provider, model)

            try:
                return await breaker.call_async(func, *args, **kwargs)
            except CircuitBreakerError:
                logger.error(
                    "circuit_breaker_blocked_call",
                    provider=provider,
                    model=model,
                    function=func.__name__
                )
                raise ModelAPIError(
                    f"Circuit breaker OPEN for {provider}:{model}. Service unavailable.",
                    context={"provider": provider, "model": model, "breaker_state": "open"}
                )

        def sync_wrapper(*args, **kwargs):
            breaker = CircuitBreakerRegistry.get_breaker(provider, model)

            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerError:
                logger.error(
                    "circuit_breaker_blocked_call",
                    provider=provider,
                    model=model,
                    function=func.__name__
                )
                raise ModelAPIError(
                    f"Circuit breaker OPEN for {provider}:{model}. Service unavailable.",
                    context={"provider": provider, "model": model, "breaker_state": "open"}
                )

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

def get_provider_health() -> Dict[str, dict]:
    """
    Get health status of all AI providers

    Returns:
        Dict mapping provider to health info:
        {
            "openai": {"state": "closed", "available": True},
            "anthropic": {"state": "open", "available": False},
            ...
        }
    """
    states = CircuitBreakerRegistry.get_all_states()

    health = {}
    for key, state in states.items():
        provider = key.split(":")[0]

        if provider not in health:
            health[provider] = {
                "state": state,
                "available": state == "closed",
                "models": {}
            }

        # If key includes model name
        if ":" in key:
            model = key.split(":")[1]
            health[provider]["models"][model] = {
                "state": state,
                "available": state == "closed"
            }

    return health
