"""
Test Error Handling Infrastructure

Tests retry decorators, circuit breakers, and fallback chain.
"""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
import os

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.retry_decorators import ai_api_retry, openai_retry
from ai.circuit_breakers import CircuitBreakerRegistry, with_circuit_breaker
from ai.fallback import AIFallbackChain
from core.exceptions import ModelAPIError
from utils.logging import configure_logging


async def test_retry_decorator():
    """Test retry decorator with simulated failures"""
    print("\n" + "=" * 70)
    print("TEST 1: Retry Decorator")
    print("=" * 70)

    attempt_count = 0

    @ai_api_retry(max_attempts=3, min_wait=1, max_wait=3)
    async def flaky_api_call():
        nonlocal attempt_count
        attempt_count += 1
        print(f"   Attempt {attempt_count}")

        if attempt_count < 3:
            raise ModelAPIError("Simulated API failure")

        return "Success after retries!"

    try:
        result = await flaky_api_call()
        print(f"✅ Result: {result}")
        print(f"   Total attempts: {attempt_count}")
    except Exception as e:
        print(f"❌ Failed: {e}")


async def test_circuit_breaker():
    """Test circuit breaker pattern"""
    print("\n" + "=" * 70)
    print("TEST 2: Circuit Breaker")
    print("=" * 70)

    # Get circuit breaker for test provider
    breaker = CircuitBreakerRegistry.get_breaker("test_provider")

    print(f"   Initial state: {breaker.current_state}")

    # Simulate failures to open circuit
    for i in range(6):  # fail_max is 5 for default
        try:
            @with_circuit_breaker("test_provider")
            async def failing_call():
                raise ModelAPIError("Simulated failure")

            await failing_call()
        except ModelAPIError:
            print(f"   Failure {i+1}: Circuit state = {breaker.current_state}")

    # Try to call again (should be blocked by open circuit)
    try:
        @with_circuit_breaker("test_provider")
        async def blocked_call():
            return "This should not execute"

        await blocked_call()
    except ModelAPIError as e:
        print(f"✅ Circuit blocked call: {e}")

    print(f"   Final state: {breaker.current_state}")


async def test_fallback_chain():
    """Test AI fallback chain"""
    print("\n" + "=" * 70)
    print("TEST 3: Fallback Chain")
    print("=" * 70)

    # Load API keys
    load_dotenv()

    api_keys = {}
    if os.getenv("OPENAI_API_KEY"):
        api_keys["openai"] = os.getenv("OPENAI_API_KEY")
    if os.getenv("ANTHROPIC_API_KEY"):
        api_keys["anthropic"] = os.getenv("ANTHROPIC_API_KEY")
    if os.getenv("GOOGLE_API_KEY"):
        api_keys["google"] = os.getenv("GOOGLE_API_KEY")

    if not api_keys:
        print("⏭️  Skipped (no API keys in .env)")
        return

    # Create fallback chain
    fallback = AIFallbackChain(
        primary_model="gpt-4o-mini",
        api_keys=api_keys,
        enable_sovereign_fallback=False  # Disable Ollama for this test
    )

    # Get chain info
    chain_info = fallback.get_chain_info()

    print(f"\n   Fallback chain ({len(chain_info)} models):")
    for model_info in chain_info:
        status = "✅" if model_info["usable"] else "❌"
        print(f"   {status} Priority {model_info['priority']}: {model_info['model']}")
        print(f"      Provider: {model_info['provider']}")
        print(f"      Reason: {model_info['reason']}")
        print(f"      Available: {model_info['available']}, Has API Key: {model_info['has_api_key']}")

    # Test actual fallback with a simple request
    try:
        print(f"\n   Testing fallback with simple request...")
        response = await fallback.generate_with_fallback(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello from fallback chain!'"}
            ],
            temperature=0.7,
            max_tokens=50
        )

        print(f"✅ Fallback succeeded!")
        print(f"   Model used: {response.model}")
        print(f"   Response: {response.content}")

    except Exception as e:
        print(f"❌ Fallback failed: {e}")


async def test_provider_health():
    """Test provider health check"""
    print("\n" + "=" * 70)
    print("TEST 4: Provider Health Check")
    print("=" * 70)

    from ai.circuit_breakers import get_provider_health

    health = get_provider_health()

    if not health:
        print("   No providers registered yet")
        return

    for provider, info in health.items():
        status = "✅" if info["available"] else "❌"
        print(f"   {status} {provider}: {info['state']}")

        if info.get("models"):
            for model, model_info in info["models"].items():
                model_status = "✅" if model_info["available"] else "❌"
                print(f"      {model_status} {model}: {model_info['state']}")


async def main():
    """Run all error handling tests"""
    print("=" * 70)
    print("🧪 ERROR HANDLING INFRASTRUCTURE TESTS")
    print("=" * 70)

    # Configure logging
    configure_logging(log_level="INFO", console_output=True)

    # Run tests
    await test_retry_decorator()
    await test_circuit_breaker()
    await test_fallback_chain()
    await test_provider_health()

    print("\n" + "=" * 70)
    print("✅ Error handling tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
