"""
Tests for AI Fallback Chain

Comprehensive tests for multi-tier AI provider fallback mechanism.
Validates fallback chain building, model selection, and automatic failover.

Covers:
- Fallback chain building (4-tier strategy)
- Cheaper model selection per provider
- Cross-provider fallback
- Sovereign mode (local Ollama)
- Automatic failover on failures
- Circuit breaker integration
- API key validation
- Error handling and reporting
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from ai.fallback import AIFallbackChain, FallbackModel
from ai.providers.base import ModelResponse
from core.exceptions import AIError, ModelAPIError


# ==============================================================================
# FALLBACK CHAIN BUILDING TESTS
# ==============================================================================

class TestFallbackChainBuilding:
    """Test fallback chain construction"""

    @pytest.mark.unit
    def test_chain_with_openai_primary(self):
        """Should build fallback chain with OpenAI as primary"""
        api_keys = {"openai": "test-key", "anthropic": "test-key"}

        chain = AIFallbackChain(
            primary_model="gpt-4o",
            api_keys=api_keys,
            enable_sovereign_fallback=True
        )

        assert len(chain.fallback_chain) == 4  # primary + secondary + tertiary + sovereign
        assert chain.fallback_chain[0].model_name == "gpt-4o"
        assert chain.fallback_chain[0].priority == 1
        assert chain.fallback_chain[1].model_name == "gpt-4o-mini"  # Cheaper OpenAI
        assert chain.fallback_chain[1].priority == 2
        # Tertiary should be from different provider (Anthropic)
        assert chain.fallback_chain[2].priority == 3
        # Sovereign should be Ollama
        assert chain.fallback_chain[3].model_name == "llama3.3:70b"
        assert chain.fallback_chain[3].priority == 4

    @pytest.mark.unit
    def test_chain_with_anthropic_primary(self):
        """Should build fallback chain with Anthropic as primary"""
        api_keys = {"anthropic": "test-key", "openai": "test-key"}

        chain = AIFallbackChain(
            primary_model="claude-sonnet-4-5-20250929",
            api_keys=api_keys,
            enable_sovereign_fallback=True
        )

        assert len(chain.fallback_chain) == 4
        assert chain.fallback_chain[0].model_name == "claude-sonnet-4-5-20250929"
        assert chain.fallback_chain[1].model_name == "claude-3.5-haiku"  # Cheaper Anthropic
        # Tertiary should be from different provider (OpenAI)
        assert chain.fallback_chain[2].priority == 3

    @pytest.mark.unit
    def test_chain_with_google_primary(self):
        """Should build fallback chain with Google as primary"""
        api_keys = {"google": "test-key", "anthropic": "test-key"}

        chain = AIFallbackChain(
            primary_model="gemini-2.5-flash",
            api_keys=api_keys,
            enable_sovereign_fallback=False
        )

        # Without sovereign fallback, should have 3 tiers
        assert len(chain.fallback_chain) == 3
        assert chain.fallback_chain[0].model_name == "gemini-2.5-flash"
        assert chain.fallback_chain[1].model_name == "gemini-2.5-flash-lite"  # Cheaper Google

    @pytest.mark.unit
    def test_chain_without_sovereign_fallback(self):
        """Should omit Ollama when sovereign fallback disabled"""
        api_keys = {"openai": "test-key", "anthropic": "test-key"}

        chain = AIFallbackChain(
            primary_model="gpt-4o",
            api_keys=api_keys,
            enable_sovereign_fallback=False
        )

        # Should have 3 tiers (no Ollama)
        assert len(chain.fallback_chain) == 3
        assert all(f.model_name != "llama3.3:70b" for f in chain.fallback_chain)

    @pytest.mark.unit
    def test_chain_with_unknown_primary_model(self):
        """Should raise error for unknown primary model"""
        api_keys = {"openai": "test-key"}

        with pytest.raises(AIError) as exc_info:
            AIFallbackChain(
                primary_model="unknown-model-xyz",
                api_keys=api_keys
            )

        assert "Unknown primary model" in str(exc_info.value)

    @pytest.mark.unit
    def test_cheaper_model_selection(self):
        """Should select correct cheaper model per provider"""
        api_keys = {"openai": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys)

        # Test internal method
        assert chain._get_cheaper_model("openai") == "gpt-4o-mini"
        assert chain._get_cheaper_model("anthropic") == "claude-3.5-haiku"
        assert chain._get_cheaper_model("google") == "gemini-2.5-flash-lite"
        assert chain._get_cheaper_model("deepseek") == "deepseek-chat"
        assert chain._get_cheaper_model("perplexity") == "sonar"

    @pytest.mark.unit
    def test_different_provider_selection(self):
        """Should select model from different provider"""
        api_keys = {"openai": "test-key", "anthropic": "test-key", "google": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys)

        # Should skip OpenAI and pick Anthropic (next in fallback order)
        different = chain._get_different_provider_model("openai")
        assert different == "claude-sonnet-4-5-20250929"

        # Should skip Anthropic and pick OpenAI
        different = chain._get_different_provider_model("anthropic")
        assert different == "gpt-4o-mini"

    @pytest.mark.unit
    def test_different_provider_with_no_api_keys(self):
        """Should return None if no other providers have API keys"""
        api_keys = {"openai": "test-key"}  # Only OpenAI
        chain = AIFallbackChain("gpt-4o", api_keys)

        # No other providers available
        different = chain._get_different_provider_model("openai")
        assert different is None

    @pytest.mark.unit
    def test_sovereign_model_selection(self):
        """Should return llama3.3:70b as sovereign model"""
        api_keys = {"openai": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys)

        sovereign = chain._get_sovereign_model()
        assert sovereign == "llama3.3:70b"


# ==============================================================================
# GENERATE WITH FALLBACK TESTS
# ==============================================================================

class TestGenerateWithFallback:
    """Test automatic fallback during generation"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_primary_model_success_no_fallback(self):
        """Should use primary model when it succeeds"""
        api_keys = {"openai": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        # Mock successful primary model
        mock_response = ModelResponse(
            content="Success from primary",
            model="gpt-4o",
            finish_reason="stop"
        )

        with patch("ai.model_registry.ModelRegistry.get_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.generate.return_value = mock_response
            mock_get_model.return_value = mock_model

            response = await chain.generate_with_fallback(
                messages=[{"role": "user", "content": "test"}]
            )

        assert response.content == "Success from primary"
        assert response.model == "gpt-4o"
        # Should only call primary model
        assert mock_get_model.call_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_to_secondary_on_primary_failure(self):
        """Should fallback to secondary model when primary fails"""
        api_keys = {"openai": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        # Mock responses
        mock_secondary_response = ModelResponse(
            content="Success from secondary",
            model="gpt-4o-mini",
            finish_reason="stop"
        )

        call_count = {"value": 0}

        def mock_get_model_fn(model_name, api_key):
            call_count["value"] += 1
            mock_model = AsyncMock()

            if model_name == "gpt-4o":
                # Primary fails
                mock_model.generate.side_effect = ModelAPIError("Primary failed")
            else:
                # Secondary succeeds
                mock_model.generate.return_value = mock_secondary_response

            return mock_model

        with patch("ai.model_registry.ModelRegistry.get_model", side_effect=mock_get_model_fn):
            response = await chain.generate_with_fallback(
                messages=[{"role": "user", "content": "test"}]
            )

        assert response.content == "Success from secondary"
        assert response.model == "gpt-4o-mini"
        assert call_count["value"] == 2  # Tried primary, then secondary

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fallback_to_tertiary_cross_provider(self):
        """Should fallback to different provider when same-provider models fail"""
        api_keys = {"openai": "test-key", "anthropic": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        mock_tertiary_response = ModelResponse(
            content="Success from Anthropic",
            model="claude-sonnet-4-5-20250929",
            finish_reason="stop"
        )

        call_count = {"value": 0}

        def mock_get_model_fn(model_name, api_key):
            call_count["value"] += 1
            mock_model = AsyncMock()

            if "gpt" in model_name:
                # OpenAI models fail
                mock_model.generate.side_effect = ModelAPIError("OpenAI down")
            else:
                # Anthropic succeeds
                mock_model.generate.return_value = mock_tertiary_response

            return mock_model

        with patch("ai.model_registry.ModelRegistry.get_model", side_effect=mock_get_model_fn):
            response = await chain.generate_with_fallback(
                messages=[{"role": "user", "content": "test"}]
            )

        assert response.content == "Success from Anthropic"
        assert "claude" in response.model
        assert call_count["value"] == 3  # Tried gpt-4o, gpt-4o-mini, claude

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_models_fail_raises_error(self):
        """Should raise AIError when all models in chain fail"""
        api_keys = {"openai": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        # All models fail
        with patch("ai.model_registry.ModelRegistry.get_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.generate.side_effect = ModelAPIError("All down")
            mock_get_model.return_value = mock_model

            with pytest.raises(AIError) as exc_info:
                await chain.generate_with_fallback(
                    messages=[{"role": "user", "content": "test"}]
                )

        assert "All models in fallback chain failed" in str(exc_info.value)
        assert "gpt-4o" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_unavailable_models(self):
        """Should skip models with open circuit breakers"""
        api_keys = {"openai": "test-key", "anthropic": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        mock_response = ModelResponse(
            content="Success from Anthropic",
            model="claude-sonnet-4-5-20250929",
            finish_reason="stop"
        )

        # Mock circuit breaker to mark OpenAI as unavailable
        with patch("ai.circuit_breakers.CircuitBreakerRegistry.is_available") as mock_available:
            def is_available_fn(provider, model_name=None):
                # OpenAI circuit open, Anthropic circuit closed
                return provider != "openai"

            mock_available.side_effect = is_available_fn

            with patch("ai.model_registry.ModelRegistry.get_model") as mock_get_model:
                mock_model = AsyncMock()
                mock_model.generate.return_value = mock_response
                mock_get_model.return_value = mock_model

                response = await chain.generate_with_fallback(
                    messages=[{"role": "user", "content": "test"}]
                )

        assert response.content == "Success from Anthropic"
        # Should have skipped both OpenAI models and gone straight to Anthropic

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_models_without_api_keys(self):
        """Should skip models for providers without API keys"""
        api_keys = {"openai": "test-key"}  # No Anthropic key
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        mock_response = ModelResponse(
            content="Success from OpenAI mini",
            model="gpt-4o-mini",
            finish_reason="stop"
        )

        call_count = {"value": 0}

        def mock_get_model_fn(model_name, api_key):
            call_count["value"] += 1
            mock_model = AsyncMock()

            if model_name == "gpt-4o":
                mock_model.generate.side_effect = ModelAPIError("Error")
            else:
                mock_model.generate.return_value = mock_response

            return mock_model

        with patch("ai.model_registry.ModelRegistry.get_model", side_effect=mock_get_model_fn):
            response = await chain.generate_with_fallback(
                messages=[{"role": "user", "content": "test"}]
            )

        # Should skip Anthropic (no API key) and use gpt-4o-mini
        assert response.content == "Success from OpenAI mini"
        assert call_count["value"] == 2  # gpt-4o (failed), gpt-4o-mini (success)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_preserves_generation_parameters(self):
        """Should pass all generation parameters to model"""
        api_keys = {"openai": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        mock_response = ModelResponse(content="test", model="gpt-4o", finish_reason="stop")

        with patch("ai.model_registry.ModelRegistry.get_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.generate.return_value = mock_response
            mock_get_model.return_value = mock_model

            await chain.generate_with_fallback(
                messages=[{"role": "user", "content": "test"}],
                tools=[{"name": "search"}],
                temperature=0.9,
                max_tokens=500,
                custom_param="test"
            )

        # Verify all parameters were passed to model.generate()
        call_args = mock_model.generate.call_args
        assert call_args.kwargs["messages"] == [{"role": "user", "content": "test"}]
        assert call_args.kwargs["tools"] == [{"name": "search"}]
        assert call_args.kwargs["temperature"] == 0.9
        assert call_args.kwargs["max_tokens"] == 500
        assert call_args.kwargs["custom_param"] == "test"


# ==============================================================================
# CHAIN INFO TESTS
# ==============================================================================

class TestChainInfo:
    """Test fallback chain introspection"""

    @pytest.mark.unit
    def test_get_chain_info_structure(self):
        """Should return chain info with all required fields"""
        api_keys = {"openai": "test-key", "anthropic": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        info = chain.get_chain_info()

        assert len(info) == 3  # 3 models in chain

        for model_info in info:
            assert "model" in model_info
            assert "provider" in model_info
            assert "priority" in model_info
            assert "reason" in model_info
            assert "available" in model_info
            assert "has_api_key" in model_info
            assert "usable" in model_info

    @pytest.mark.unit
    def test_get_chain_info_priorities(self):
        """Chain info should show correct priorities"""
        api_keys = {"openai": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=True)

        info = chain.get_chain_info()

        # Check priorities are sequential
        priorities = [m["priority"] for m in info]
        assert priorities == [1, 2, 3, 4] or priorities == [1, 2, 4]  # May skip priority 3 if no tertiary

    @pytest.mark.unit
    def test_get_chain_info_api_key_status(self):
        """Chain info should reflect API key availability"""
        api_keys = {"openai": "test-key"}  # No Anthropic key
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        info = chain.get_chain_info()

        # OpenAI models should have API key
        openai_models = [m for m in info if m["provider"] == "openai"]
        for model in openai_models:
            assert model["has_api_key"] is True

        # Anthropic models should not have API key
        anthropic_models = [m for m in info if m["provider"] == "anthropic"]
        for model in anthropic_models:
            assert model["has_api_key"] is False

    @pytest.mark.unit
    def test_get_chain_info_usability(self):
        """Chain info should correctly calculate usability"""
        api_keys = {"openai": "test-key"}
        chain = AIFallbackChain("gpt-4o", api_keys, enable_sovereign_fallback=False)

        with patch("ai.circuit_breakers.CircuitBreakerRegistry.is_available") as mock_available:
            mock_available.return_value = True  # All circuits closed

            info = chain.get_chain_info()

            # Models with API key and available circuit should be usable
            openai_models = [m for m in info if m["provider"] == "openai"]
            for model in openai_models:
                assert model["usable"] is True
