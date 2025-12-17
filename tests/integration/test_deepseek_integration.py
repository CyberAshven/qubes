#!/usr/bin/env python3
"""
Test DeepSeek integration end-to-end
"""
import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from ai.model_registry import ModelRegistry
from ai.fallback import AIFallbackChain

async def test_deepseek_direct():
    """Test DeepSeek model directly"""
    print("=" * 60)
    print("Test 1: Direct DeepSeek Model Instantiation")
    print("=" * 60)

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ FAIL: DEEPSEEK_API_KEY not found in environment")
        return False

    print(f"✓ API key found: {api_key[:10]}...")

    # Get model info
    model_info = ModelRegistry.get_model_info("deepseek-chat")
    if not model_info:
        print("❌ FAIL: deepseek-chat not in model registry")
        return False

    print(f"✓ Model info: provider={model_info['provider']}, class={model_info['class'].__name__}")

    # Instantiate model
    try:
        model = ModelRegistry.get_model("deepseek-chat", api_key)
        print(f"✓ Model instantiated: {type(model).__name__}")
    except Exception as e:
        print(f"❌ FAIL: Could not instantiate model: {e}")
        return False

    # Test generation
    try:
        messages = [
            {"role": "user", "content": "Say 'Hello World' and nothing else."}
        ]
        response = await model.generate(messages, temperature=0.7)
        print(f"✓ Generation successful!")
        print(f"  Response: {response.content[:100]}...")
        print(f"  Tokens: {response.usage.get('total_tokens', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ FAIL: Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_fallback_chain():
    """Test fallback chain with DeepSeek as primary"""
    print("\n" + "=" * 60)
    print("Test 2: Fallback Chain with DeepSeek Primary")
    print("=" * 60)

    api_keys = {}

    # Collect all available API keys
    if os.getenv("OPENAI_API_KEY"):
        api_keys["openai"] = os.getenv("OPENAI_API_KEY")
        print(f"✓ OpenAI key: {api_keys['openai'][:10]}...")

    if os.getenv("ANTHROPIC_API_KEY"):
        api_keys["anthropic"] = os.getenv("ANTHROPIC_API_KEY")
        print(f"✓ Anthropic key: {api_keys['anthropic'][:10]}...")

    if os.getenv("GOOGLE_API_KEY"):
        api_keys["google"] = os.getenv("GOOGLE_API_KEY")
        print(f"✓ Google key: {api_keys['google'][:10]}...")

    if os.getenv("DEEPSEEK_API_KEY"):
        api_keys["deepseek"] = os.getenv("DEEPSEEK_API_KEY")
        print(f"✓ DeepSeek key: {api_keys['deepseek'][:10]}...")

    if os.getenv("PERPLEXITY_API_KEY"):
        api_keys["perplexity"] = os.getenv("PERPLEXITY_API_KEY")
        print(f"✓ Perplexity key: {api_keys['perplexity'][:10]}...")

    print(f"\nTotal API keys available: {len(api_keys)}")

    # Create fallback chain
    try:
        chain = AIFallbackChain(
            primary_model="deepseek-chat",
            api_keys=api_keys,
            enable_sovereign_fallback=False  # Disable Ollama for this test
        )
        print(f"✓ Fallback chain created")
    except Exception as e:
        print(f"❌ FAIL: Could not create fallback chain: {e}")
        return False

    # Show chain info
    chain_info = chain.get_chain_info()
    print(f"\nFallback chain ({len(chain_info)} models):")
    for i, info in enumerate(chain_info, 1):
        status = "✓" if info['usable'] else "✗"
        print(f"  {i}. [{status}] {info['model']} ({info['provider']}) - {info['reason']}")
        print(f"      available={info['available']}, has_api_key={info['has_api_key']}")

    # Test generation through fallback chain
    try:
        messages = [
            {"role": "user", "content": "Say 'Hello from DeepSeek' and nothing else."}
        ]
        response = await chain.generate_with_fallback(messages, temperature=0.7)
        print(f"\n✓ Generation through fallback chain successful!")
        print(f"  Response: {response.content[:100]}...")
        print(f"  Model used: {response.model}")
        print(f"  Tokens: {response.usage.get('total_tokens', 'N/A')}")

        # Check if primary model was used (not fallback)
        if response.model == "deepseek-chat":
            print(f"  ✓ PRIMARY MODEL USED (no fallback needed)")
            return True
        else:
            print(f"  ⚠ FALLBACK WAS USED: {response.model}")
            print(f"  This means the primary model (deepseek-chat) failed!")
            return False

    except Exception as e:
        print(f"❌ FAIL: Generation through fallback chain failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("\n" + "=" * 60)
    print("DEEPSEEK INTEGRATION TEST SUITE")
    print("=" * 60)

    # Test 1: Direct model
    test1_passed = await test_deepseek_direct()

    # Test 2: Fallback chain
    test2_passed = await test_fallback_chain()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Test 1 (Direct Model):    {'✓ PASS' if test1_passed else '✗ FAIL'}")
    print(f"Test 2 (Fallback Chain):  {'✓ PASS' if test2_passed else '✗ FAIL'}")
    print("=" * 60)

    if test1_passed and test2_passed:
        print("\n✓ ALL TESTS PASSED - DeepSeek integration is working!")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED - See above for details")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
