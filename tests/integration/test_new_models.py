"""
Test script for DeepSeek and LLaMA 3.2 model loading

Validates that:
1. DeepSeek models are registered correctly
2. LLaMA 3.2 models are registered correctly
3. DeepSeek provider can be instantiated
4. Model registry returns correct provider classes
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ai.model_registry import ModelRegistry
from ai.providers import DeepSeekModel, OllamaModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_model_registry():
    """Test that new models are in the registry"""
    print("=" * 60)
    print("Testing Model Registry")
    print("=" * 60)

    # Test DeepSeek models
    deepseek_models = ["deepseek-chat", "deepseek-reasoner"]
    print("\n1. DeepSeek Models:")
    for model_name in deepseek_models:
        info = ModelRegistry.get_model_info(model_name)
        if info:
            print(f"   ✓ {model_name}: {info['description']}")
            assert info['provider'] == 'deepseek', f"Expected provider 'deepseek', got '{info['provider']}'"
            assert info['class'] == DeepSeekModel, f"Expected DeepSeekModel class"
        else:
            print(f"   ✗ {model_name}: NOT FOUND")
            sys.exit(1)

    # Test LLaMA 3.2 models
    llama32_models = [
        "llama3.2",
        "llama3.2:1b",
        "llama3.2:3b",
        "llama3.2-vision:11b",
        "llama3.2-vision:90b"
    ]
    print("\n2. LLaMA 3.2 Models:")
    for model_name in llama32_models:
        info = ModelRegistry.get_model_info(model_name)
        if info:
            print(f"   ✓ {model_name}: {info['description']}")
            assert info['provider'] == 'ollama', f"Expected provider 'ollama', got '{info['provider']}'"
            assert info['class'] == OllamaModel, f"Expected OllamaModel class"
        else:
            print(f"   ✗ {model_name}: NOT FOUND")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ All models registered correctly!")
    print("=" * 60)

def test_deepseek_provider():
    """Test DeepSeek provider instantiation"""
    print("\n" + "=" * 60)
    print("Testing DeepSeek Provider")
    print("=" * 60)

    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

    if not deepseek_api_key:
        print("\n⚠ WARNING: DEEPSEEK_API_KEY not found in .env")
        print("   Set DEEPSEEK_API_KEY to test DeepSeek provider instantiation")
        return

    print(f"\n✓ DeepSeek API Key found: {deepseek_api_key[:10]}...{deepseek_api_key[-4:]}")

    # Test instantiation via ModelRegistry
    try:
        model = ModelRegistry.get_model("deepseek-chat", api_key=deepseek_api_key)
        print(f"✓ Successfully loaded deepseek-chat")
        print(f"   - Provider class: {model.__class__.__name__}")
        print(f"   - Model name: {model.model_name}")
        print(f"   - Context window: {model.get_context_window():,} tokens")

        # Test cost estimation
        cost = model.estimate_cost(1000, 500)
        print(f"   - Est. cost (1k in, 500 out): ${cost:.4f}")

    except Exception as e:
        print(f"\n✗ Failed to load deepseek-chat: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ DeepSeek provider working!")
    print("=" * 60)

def test_provider_list():
    """Test that deepseek is in the provider list"""
    print("\n" + "=" * 60)
    print("Testing Provider List")
    print("=" * 60)

    providers = ModelRegistry.get_providers()
    print(f"\nAvailable providers: {', '.join(providers)}")

    expected_providers = ['anthropic', 'deepseek', 'google', 'ollama', 'openai', 'perplexity']
    for provider in expected_providers:
        if provider in providers:
            print(f"   ✓ {provider}")
        else:
            print(f"   ✗ {provider} MISSING")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ All providers available!")
    print("=" * 60)

def test_model_counts():
    """Count models per provider"""
    print("\n" + "=" * 60)
    print("Model Count by Provider")
    print("=" * 60)

    for provider in ModelRegistry.get_providers():
        models = ModelRegistry.list_models(provider=provider)
        print(f"\n{provider.upper()}: {len(models)} models")
        for name, info in models.items():
            print(f"   - {name}: {info['description']}")

    total = len(ModelRegistry.MODELS)
    print("\n" + "=" * 60)
    print(f"Total models registered: {total}")
    print("=" * 60)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("QUBES - DeepSeek & LLaMA 3.2 Integration Test")
    print("=" * 60)

    try:
        test_model_registry()
        test_provider_list()
        test_deepseek_provider()
        test_model_counts()

        print("\n" + "=" * 60)
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("=" * 60)
        print("\nDeepSeek and LLaMA 3.2 integration complete!")
        print("\nYou can now use:")
        print("  - deepseek-chat (DeepSeek-V3.2, $0.27/M input)")
        print("  - deepseek-reasoner (DeepSeek-R1, advanced reasoning)")
        print("  - llama3.2, llama3.2:1b, llama3.2:3b (local)")
        print("  - llama3.2-vision:11b, llama3.2-vision:90b (multimodal)")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗✗✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
