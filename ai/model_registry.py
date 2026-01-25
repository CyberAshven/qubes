"""
AI Model Registry

Registry of available AI models across all providers.
Matches documentation in docs/09_AI_Integration_Tool_Calling.md Section 6.1
"""

from typing import Dict, Any, Optional

from ai.providers import (
    AIModelInterface,
    OpenAIModel,
    AnthropicModel,
    GoogleModel,
    PerplexityModel,
    OllamaModel,
    DeepSeekModel,
    VeniceModel,
    NanoGPTModel
)
from core.exceptions import AIError
from utils.logging import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """
    Registry of available AI models (Updated: January 2026)

    Latest models across 7 providers with support for reasoning,
    vision, and extended context windows.
    """

    # Pricing is average of input/output costs per 1k tokens (approximate, 2025 rates)
    MODELS: Dict[str, Dict[str, Any]] = {
        # OpenAI - Latest models (2025-2026)
        "gpt-5.2": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.2, Dec 2025, 256k context", "temperature_fixed": 1.0, "cost_per_1k_tokens": 0.015},
        # Note: gpt-5.2-pro removed - requires OpenAI Responses API which we don't support
        "gpt-5.2-chat-latest": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.2 Chat, 256k context", "cost_per_1k_tokens": 0.010},
        "gpt-5.2-codex": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.2 Codex, 256k context", "cost_per_1k_tokens": 0.012},
        "gpt-5.1": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.1, 256k context", "temperature_fixed": 1.0, "cost_per_1k_tokens": 0.012},
        "gpt-5.1-chat-latest": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.1 Chat, 256k context", "cost_per_1k_tokens": 0.008},
        "gpt-5-turbo": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5 Turbo, 256k context", "cost_per_1k_tokens": 0.006},
        "gpt-5": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5, Aug 2025, 256k context", "temperature_fixed": 1.0, "cost_per_1k_tokens": 0.010},
        "gpt-5-mini": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5 Mini, 128k context", "cost_per_1k_tokens": 0.002},
        "gpt-4.1": {"provider": "openai", "class": OpenAIModel, "description": "GPT-4.1, 1M context", "cost_per_1k_tokens": 0.008},
        "gpt-4.1-mini": {"provider": "openai", "class": OpenAIModel, "description": "GPT-4.1 Mini, 128k context", "cost_per_1k_tokens": 0.002},
        "gpt-4o": {"provider": "openai", "class": OpenAIModel, "description": "GPT-4o, multimodal, 128k context", "cost_per_1k_tokens": 0.005},
        "gpt-4o-mini": {"provider": "openai", "class": OpenAIModel, "description": "GPT-4o Mini, 128k context", "cost_per_1k_tokens": 0.0004},
        "o4": {"provider": "openai", "class": OpenAIModel, "description": "O4 reasoning, 200k context", "temperature_fixed": 1.0, "cost_per_1k_tokens": 0.020},
        "o4-mini": {"provider": "openai", "class": OpenAIModel, "description": "O4 Mini reasoning, 200k context", "temperature_fixed": 1.0, "cost_per_1k_tokens": 0.006},
        "o3-mini": {"provider": "openai", "class": OpenAIModel, "description": "O3 Mini reasoning, 200k context", "temperature_fixed": 1.0, "cost_per_1k_tokens": 0.004},
        "o1": {"provider": "openai", "class": OpenAIModel, "description": "O1 reasoning, 200k context", "temperature_fixed": 1.0, "cost_per_1k_tokens": 0.015},

        # Anthropic - Claude 4 generation (2025)
        "claude-sonnet-4-5-20250929": {"provider": "anthropic", "class": AnthropicModel, "description": "Claude 4.5 Sonnet, Sep 2025, 200k context", "cost_per_1k_tokens": 0.009},
        "claude-opus-4-1-20250805": {"provider": "anthropic", "class": AnthropicModel, "description": "Claude 4.1 Opus, Aug 2025, 200k context", "cost_per_1k_tokens": 0.045},
        "claude-opus-4-20250514": {"provider": "anthropic", "class": AnthropicModel, "description": "Claude 4 Opus, May 2025, 200k context", "cost_per_1k_tokens": 0.045},
        "claude-sonnet-4-20250514": {"provider": "anthropic", "class": AnthropicModel, "description": "Claude 4 Sonnet, 1M context", "cost_per_1k_tokens": 0.009},
        "claude-3-7-sonnet-20250219": {"provider": "anthropic", "class": AnthropicModel, "description": "Claude 3.7 Sonnet, Feb 2025, 200k context", "cost_per_1k_tokens": 0.006},
        "claude-3-5-haiku-20241022": {"provider": "anthropic", "class": AnthropicModel, "description": "Claude 3.5 Haiku, Oct 2024, 200k context", "cost_per_1k_tokens": 0.001},
        "claude-3-haiku-20240307": {"provider": "anthropic", "class": AnthropicModel, "description": "Claude 3 Haiku, Mar 2024, 200k context", "cost_per_1k_tokens": 0.0005},
        # Anthropic aliases (short names for convenience)
        "claude-opus-4-1": {"provider": "anthropic", "class": AnthropicModel, "alias_for": "claude-opus-4-1-20250805", "description": "Alias for Claude Opus 4.1", "cost_per_1k_tokens": 0.045},
        "claude-opus-4": {"provider": "anthropic", "class": AnthropicModel, "alias_for": "claude-opus-4-20250514", "description": "Alias for Claude Opus 4", "cost_per_1k_tokens": 0.045},
        "claude-sonnet-4-5": {"provider": "anthropic", "class": AnthropicModel, "alias_for": "claude-sonnet-4-5-20250929", "description": "Alias for Claude Sonnet 4.5", "cost_per_1k_tokens": 0.009},
        "claude-sonnet-4": {"provider": "anthropic", "class": AnthropicModel, "alias_for": "claude-sonnet-4-20250514", "description": "Alias for Claude Sonnet 4", "cost_per_1k_tokens": 0.009},
        "claude-3-7-sonnet": {"provider": "anthropic", "class": AnthropicModel, "alias_for": "claude-3-7-sonnet-20250219", "description": "Alias for Claude 3.7 Sonnet", "cost_per_1k_tokens": 0.006},
        "claude-3-5-haiku": {"provider": "anthropic", "class": AnthropicModel, "alias_for": "claude-3-5-haiku-20241022", "description": "Alias for Claude 3.5 Haiku", "cost_per_1k_tokens": 0.001},
        "claude-3-haiku": {"provider": "anthropic", "class": AnthropicModel, "alias_for": "claude-3-haiku-20240307", "description": "Alias for Claude 3 Haiku", "cost_per_1k_tokens": 0.0005},

        # Google - Gemini 3 and 2.5 generation (2025-2026)
        "gemini-3-pro-preview": {"provider": "google", "class": GoogleModel, "description": "Gemini 3 Pro Preview, multimodal, 2M context", "cost_per_1k_tokens": 0.004},
        "gemini-3-flash-preview": {"provider": "google", "class": GoogleModel, "description": "Gemini 3 Flash Preview, 1M context", "cost_per_1k_tokens": 0.001},
        "gemini-3-pro-image-preview": {"provider": "google", "class": GoogleModel, "description": "Gemini 3 Pro Image Preview, 2M context", "cost_per_1k_tokens": 0.004},
        "gemini-2.5-pro": {"provider": "google", "class": GoogleModel, "description": "Gemini 2.5 Pro, 2M context", "cost_per_1k_tokens": 0.003},
        "gemini-2.5-flash": {"provider": "google", "class": GoogleModel, "description": "Gemini 2.5 Flash, 1M context", "cost_per_1k_tokens": 0.0005},
        "gemini-2.5-flash-preview-09-2025": {"provider": "google", "class": GoogleModel, "description": "Gemini 2.5 Flash Preview, Sep 2025, 1M context", "cost_per_1k_tokens": 0.0005},
        "gemini-2.5-flash-lite": {"provider": "google", "class": GoogleModel, "description": "Gemini 2.5 Flash Lite, 1M context", "cost_per_1k_tokens": 0.0002},
        "gemini-2.0-flash": {"provider": "google", "class": GoogleModel, "description": "Gemini 2.0 Flash, Jan 2025, 1M context", "cost_per_1k_tokens": 0.0003},
        "gemini-1.5-pro": {"provider": "google", "class": GoogleModel, "description": "Gemini 1.5 Pro, 2M context", "cost_per_1k_tokens": 0.002},
        # Google/Gemini aliases (short names for convenience)
        "gemini-3-pro": {"provider": "google", "class": GoogleModel, "alias_for": "gemini-3-pro-preview", "description": "Alias for Gemini 3 Pro Preview", "cost_per_1k_tokens": 0.004},
        "gemini-3-flash": {"provider": "google", "class": GoogleModel, "alias_for": "gemini-3-flash-preview", "description": "Alias for Gemini 3 Flash Preview", "cost_per_1k_tokens": 0.001},
        "gemini-3": {"provider": "google", "class": GoogleModel, "alias_for": "gemini-3-pro-preview", "description": "Alias for Gemini 3 Pro Preview", "cost_per_1k_tokens": 0.004},
        "gemini-2.5": {"provider": "google", "class": GoogleModel, "alias_for": "gemini-2.5-pro", "description": "Alias for Gemini 2.5 Pro", "cost_per_1k_tokens": 0.003},
        "gemini-2": {"provider": "google", "class": GoogleModel, "alias_for": "gemini-2.0-flash", "description": "Alias for Gemini 2.0 Flash", "cost_per_1k_tokens": 0.0003},
        "gemini": {"provider": "google", "class": GoogleModel, "alias_for": "gemini-2.5-pro", "description": "Alias for Gemini 2.5 Pro (default)", "cost_per_1k_tokens": 0.003},

        # Perplexity - Sonar generation (2025)
        "sonar-pro": {"provider": "perplexity", "class": PerplexityModel, "description": "Sonar Pro, web search, 200k context", "cost_per_1k_tokens": 0.003},
        "sonar": {"provider": "perplexity", "class": PerplexityModel, "description": "Sonar, Llama 3.3 based, 128k context", "cost_per_1k_tokens": 0.001},
        "sonar-reasoning-pro": {"provider": "perplexity", "class": PerplexityModel, "description": "Sonar Reasoning Pro, 128k context", "cost_per_1k_tokens": 0.005},
        "sonar-reasoning": {"provider": "perplexity", "class": PerplexityModel, "description": "Sonar Reasoning, 128k context", "cost_per_1k_tokens": 0.002},
        "sonar-deep-research": {"provider": "perplexity", "class": PerplexityModel, "description": "Sonar Deep Research, 128k context", "cost_per_1k_tokens": 0.008},

        # DeepSeek - V3.2 and R1 (2025) - Very affordable pricing
        "deepseek-chat": {"provider": "deepseek", "class": DeepSeekModel, "description": "DeepSeek V3.2, 64k context", "cost_per_1k_tokens": 0.00014},
        "deepseek-reasoner": {"provider": "deepseek", "class": DeepSeekModel, "description": "DeepSeek R1, 64k context", "cost_per_1k_tokens": 0.00055},

        # Venice - Privacy-first AI (2025-2026)
        # Note: Venice uses specific model names - check docs.venice.ai for current list
        # Some models use prompt-based tool calling (injected into system prompt)
        "venice-uncensored": {"provider": "venice", "class": VeniceModel, "description": "Venice Uncensored 1.1 (Dolphin), 32k context", "cost_per_1k_tokens": 0.0005},
        "llama-3.3-70b": {"provider": "venice", "class": VeniceModel, "description": "Llama 3.3 70B via Venice, 128k context", "cost_per_1k_tokens": 0.001},
        "llama-3.2-3b": {"provider": "venice", "class": VeniceModel, "description": "Llama 3.2 3B via Venice, 128k context", "cost_per_1k_tokens": 0.0002},
        "qwen3-235b-a22b-instruct-2507": {"provider": "venice", "class": VeniceModel, "description": "Qwen3 235B Instruct via Venice, 128k context", "cost_per_1k_tokens": 0.003},
        "qwen3-235b-a22b-thinking-2507": {"provider": "venice", "class": VeniceModel, "description": "Qwen3 235B Thinking via Venice, 128k context", "cost_per_1k_tokens": 0.003},
        "qwen3-next-80b": {"provider": "venice", "class": VeniceModel, "description": "Qwen3 Next 80B via Venice, 128k context", "cost_per_1k_tokens": 0.002},
        "qwen3-coder-480b-a35b-instruct": {"provider": "venice", "class": VeniceModel, "description": "Qwen3 Coder 480B via Venice, 128k context", "cost_per_1k_tokens": 0.004},
        "qwen3-4b": {"provider": "venice", "class": VeniceModel, "description": "Qwen3 4B via Venice, 32k context", "cost_per_1k_tokens": 0.0002},
        "mistral-31-24b": {"provider": "venice", "class": VeniceModel, "description": "Mistral 3.1 24B via Venice, 128k context", "cost_per_1k_tokens": 0.0008},
        "claude-opus-45": {"provider": "venice", "class": VeniceModel, "description": "Claude Opus 4.5 via Venice, 200k context", "cost_per_1k_tokens": 0.050},
        "openai-gpt-52": {"provider": "venice", "class": VeniceModel, "description": "GPT-5.2 via Venice, 256k context", "cost_per_1k_tokens": 0.018},
        "openai-gpt-oss-120b": {"provider": "venice", "class": VeniceModel, "description": "OpenAI GPT OSS 120B via Venice, 128k context", "cost_per_1k_tokens": 0.002},
        "venice/gemini-3-pro": {"provider": "venice", "class": VeniceModel, "description": "Gemini 3 Pro via Venice, 2M context", "cost_per_1k_tokens": 0.005},
        "venice/gemini-3-flash": {"provider": "venice", "class": VeniceModel, "description": "Gemini 3 Flash via Venice, 1M context", "cost_per_1k_tokens": 0.002},
        "grok-41-fast": {"provider": "venice", "class": VeniceModel, "description": "Grok 4.1 via Venice, 128k context", "cost_per_1k_tokens": 0.010},
        "grok-code-fast-1": {"provider": "venice", "class": VeniceModel, "description": "Grok Code 1 via Venice, 128k context", "cost_per_1k_tokens": 0.008},
        "zai-org-glm-4.7": {"provider": "venice", "class": VeniceModel, "description": "GLM 4.7 via Venice, 128k context", "cost_per_1k_tokens": 0.002},
        "kimi-k2-thinking": {"provider": "venice", "class": VeniceModel, "description": "Kimi K2 Thinking via Venice, 256k context, 1T MoE", "cost_per_1k_tokens": 0.003},
        "minimax-m21": {"provider": "venice", "class": VeniceModel, "description": "MiniMax M2.1 via Venice, 1M context", "cost_per_1k_tokens": 0.002},
        "deepseek-v3.2": {"provider": "venice", "class": VeniceModel, "description": "DeepSeek V3.2 via Venice, 64k context", "cost_per_1k_tokens": 0.0003},
        "google-gemma-3-27b-it": {"provider": "venice", "class": VeniceModel, "description": "Gemma 3 27B via Venice, 128k context", "cost_per_1k_tokens": 0.0006},
        "hermes-3-llama-3.1-405b": {"provider": "venice", "class": VeniceModel, "description": "Hermes 3 Llama 405B via Venice, 128k context", "cost_per_1k_tokens": 0.003},
        # Legacy alias
        "dolphin-2.9.3-mistral-7b": {"provider": "venice", "class": VeniceModel, "description": "Legacy: Use venice-uncensored", "alias_for": "venice-uncensored", "cost_per_1k_tokens": 0.0005},

        # Ollama - Local models (2025) - No cost (local)
        "llama3.3:70b": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.3 70B (local), 128k context", "cost_per_1k_tokens": 0.0},
        "llama3.2": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 (local), 128k context", "cost_per_1k_tokens": 0.0},
        "llama3.2:1b": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 1B (local), 128k context", "cost_per_1k_tokens": 0.0},
        "llama3.2:3b": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 3B (local), 128k context", "cost_per_1k_tokens": 0.0},
        "llama3.2-vision:11b": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 Vision 11B (local, multimodal), 128k context", "cost_per_1k_tokens": 0.0},
        "llama3.2-vision:90b": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 Vision 90B (local, multimodal), 128k context", "cost_per_1k_tokens": 0.0},
        "qwen3:235b": {"provider": "ollama", "class": OllamaModel, "description": "Qwen3 235B (local), 128k context", "cost_per_1k_tokens": 0.0},
        "qwen3:30b": {"provider": "ollama", "class": OllamaModel, "description": "Qwen3 30B MoE (local), 128k context", "cost_per_1k_tokens": 0.0},
        "qwen2.5:7b": {"provider": "ollama", "class": OllamaModel, "description": "Qwen 2.5 7B (local), 128k context", "cost_per_1k_tokens": 0.0},
        "deepseek-r1:8b": {"provider": "ollama", "class": OllamaModel, "description": "DeepSeek R1 8B (local), 64k context", "cost_per_1k_tokens": 0.0},
        "phi4:14b": {"provider": "ollama", "class": OllamaModel, "description": "Phi-4 14B (local), 16k context", "cost_per_1k_tokens": 0.0},
        "gemma2:9b": {"provider": "ollama", "class": OllamaModel, "description": "Gemma 2 9B (local), 8k context", "cost_per_1k_tokens": 0.0},
        "mistral:7b": {"provider": "ollama", "class": OllamaModel, "description": "Mistral 7B (local), 32k context", "cost_per_1k_tokens": 0.0},
        "codellama:7b": {"provider": "ollama", "class": OllamaModel, "description": "CodeLlama 7B (local), 16k context", "cost_per_1k_tokens": 0.0},

        # NanoGPT - Pay-per-prompt service with 760+ models (2025)
        # Access to multiple providers through single API (includes NanoGPT markup)
        "nanogpt/gpt-4o": {"provider": "nanogpt", "class": NanoGPTModel, "description": "GPT-4o via NanoGPT, 128k context", "cost_per_1k_tokens": 0.006},
        "nanogpt/gpt-4o-mini": {"provider": "nanogpt", "class": NanoGPTModel, "description": "GPT-4o Mini via NanoGPT, 128k context", "cost_per_1k_tokens": 0.0006},
        "nanogpt/claude-3-5-sonnet": {"provider": "nanogpt", "class": NanoGPTModel, "description": "Claude 3.5 Sonnet via NanoGPT, 200k context", "cost_per_1k_tokens": 0.007},
        "nanogpt/claude-3-haiku": {"provider": "nanogpt", "class": NanoGPTModel, "description": "Claude 3 Haiku via NanoGPT, 200k context", "cost_per_1k_tokens": 0.0006},
        "nanogpt/llama-3.1-70b": {"provider": "nanogpt", "class": NanoGPTModel, "description": "Llama 3.1 70B via NanoGPT, 128k context", "cost_per_1k_tokens": 0.001},
        "nanogpt/llama-3.1-8b": {"provider": "nanogpt", "class": NanoGPTModel, "description": "Llama 3.1 8B via NanoGPT, 128k context", "cost_per_1k_tokens": 0.0003},
        "nanogpt/mistral-large": {"provider": "nanogpt", "class": NanoGPTModel, "description": "Mistral Large via NanoGPT, 128k context", "cost_per_1k_tokens": 0.003},
        "nanogpt/mixtral-8x7b": {"provider": "nanogpt", "class": NanoGPTModel, "description": "Mixtral 8x7B via NanoGPT, 32k context", "cost_per_1k_tokens": 0.0008},
    }

    @classmethod
    def get_model(
        cls,
        model_name: str,
        api_key: Optional[str] = None,
        **kwargs
    ) -> AIModelInterface:
        """
        Get AI model instance by name

        Args:
            model_name: Model identifier (e.g., "gpt-4o", "claude-sonnet-4")
            api_key: API key for the provider
            **kwargs: Additional provider-specific parameters

        Returns:
            Initialized AI model instance

        Raises:
            AIError: If model not found or initialization fails
        """
        model_info = cls.MODELS.get(model_name)
        if not model_info:
            # Try fuzzy matching to auto-fix slight variations in model name
            fuzzy_match = cls._find_fuzzy_match(model_name)
            if fuzzy_match:
                logger.info(
                    "model_name_auto_corrected",
                    requested=model_name,
                    corrected_to=fuzzy_match
                )
                model_name = fuzzy_match
                model_info = cls.MODELS.get(model_name)
            else:
                available_models = list(cls.MODELS.keys())
                raise AIError(
                    f"Unknown model: {model_name}",
                    context={
                        "model": model_name,
                        "available_models": available_models[:10]  # Show first 10
                    }
                )

        # Handle model aliases (legacy model names mapped to new ones)
        actual_model_name = model_info.get("alias_for", model_name)
        if actual_model_name != model_name:
            logger.info(
                "model_alias_resolved",
                requested=model_name,
                actual=actual_model_name
            )

        model_class = model_info["class"]
        provider = model_info["provider"]

        # Ollama doesn't require API key
        if provider == "ollama":
            api_key = api_key or "ollama"

        if not api_key:
            raise AIError(
                f"API key required for {provider} provider",
                context={"model": model_name, "provider": provider}
            )

        try:
            # Use the actual model name (resolved alias) for the API call
            model = model_class(model_name=actual_model_name, api_key=api_key, **kwargs)
            logger.info(
                "model_loaded",
                model=actual_model_name,
                provider=provider,
                description=model_info.get("description")
            )
            return model

        except Exception as e:
            logger.error("model_initialization_failed", model=model_name, exc_info=True)
            raise AIError(
                f"Failed to initialize {model_name}",
                context={"model": model_name, "provider": provider},
                cause=e
            )

    @classmethod
    def _find_fuzzy_match(cls, model_name: str) -> Optional[str]:
        """
        Find a fuzzy match for a model name that doesn't exactly match.

        Tries several strategies:
        1. Case-insensitive match
        2. Remove/add common suffixes (-preview, -pro, etc.)
        3. Version number normalization (2.5 vs 25, etc.)
        4. Levenshtein distance for close matches

        Args:
            model_name: The model name to find a match for

        Returns:
            The matching model name, or None if no good match found
        """
        model_lower = model_name.lower().strip()
        all_models = list(cls.MODELS.keys())

        # Strategy 1: Case-insensitive exact match
        for m in all_models:
            if m.lower() == model_lower:
                return m

        # Strategy 2: Normalize and try common variations
        # Remove/add common suffixes
        suffixes_to_try = ['-preview', '-pro', '-flash', '-lite', '']
        base_name = model_lower
        for suffix in ['-preview', '-pro-preview', '-flash-preview']:
            if base_name.endswith(suffix):
                base_name = base_name[:-len(suffix)]
                break

        # Try adding common suffixes to base name
        for suffix in suffixes_to_try:
            candidate = base_name + suffix
            for m in all_models:
                if m.lower() == candidate:
                    return m

        # Strategy 3: Version normalization (gemini-25-pro -> gemini-2.5-pro)
        import re
        # Convert "25" to "2.5", "30" to "3.0", etc.
        normalized = re.sub(r'(\d)(\d)', r'\1.\2', model_lower)
        for m in all_models:
            if m.lower() == normalized:
                return m

        # Also try without dots (gemini-2.5-pro -> gemini-25-pro pattern)
        normalized_no_dots = model_lower.replace('.', '')
        for m in all_models:
            if m.lower().replace('.', '') == normalized_no_dots:
                return m

        # Strategy 4: Prefix matching (if input is a prefix of a model name)
        matches = [m for m in all_models if m.lower().startswith(model_lower)]
        if len(matches) == 1:
            return matches[0]

        # Strategy 5: Contains matching (for partial names)
        # Only if the input is reasonably long to avoid false positives
        if len(model_lower) >= 6:
            matches = [m for m in all_models if model_lower in m.lower()]
            if len(matches) == 1:
                return matches[0]

        # Strategy 6: Simple Levenshtein distance for very close matches
        def levenshtein(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return levenshtein(s2, s1)
            if len(s2) == 0:
                return len(s1)
            prev_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                curr_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = prev_row[j + 1] + 1
                    deletions = curr_row[j] + 1
                    substitutions = prev_row[j] + (c1 != c2)
                    curr_row.append(min(insertions, deletions, substitutions))
                prev_row = curr_row
            return prev_row[-1]

        # Find closest match with edit distance <= 3
        best_match = None
        best_distance = 4  # Max distance to consider
        for m in all_models:
            dist = levenshtein(model_lower, m.lower())
            if dist < best_distance:
                best_distance = dist
                best_match = m

        if best_match:
            logger.debug(
                "fuzzy_match_found",
                requested=model_name,
                match=best_match,
                edit_distance=best_distance
            )
            return best_match

        return None

    @classmethod
    def list_models(cls, provider: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        List all available models, optionally filtered by provider

        Args:
            provider: Filter by provider (openai, anthropic, google, perplexity, ollama)

        Returns:
            Dictionary of model_name -> model_info
        """
        if provider:
            return {
                name: info
                for name, info in cls.MODELS.items()
                if info["provider"] == provider
            }
        return cls.MODELS.copy()

    @classmethod
    def get_providers(cls) -> list[str]:
        """Get list of all supported providers"""
        providers = set(info["provider"] for info in cls.MODELS.values())
        return sorted(list(providers))

    @classmethod
    def get_model_info(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a specific model"""
        return cls.MODELS.get(model_name)

    @classmethod
    def get_models_for_frontend(cls) -> Dict[str, Any]:
        """
        Return models formatted for frontend consumption.
        Groups models by provider with display names and metadata.
        """
        provider_labels = {
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "google": "Google",
            "perplexity": "Perplexity",
            "deepseek": "DeepSeek",
            "venice": "Venice (Private)",
            "ollama": "Ollama (Local)",
            "nanogpt": "NanoGPT (Pay-per-prompt)"
        }

        # Provider order for UI
        provider_order = ["openai", "anthropic", "google", "perplexity", "deepseek", "venice", "nanogpt", "ollama"]

        defaults = {
            "openai": "gpt-5.2",
            "anthropic": "claude-sonnet-4-5-20250929",
            "google": "gemini-3-flash-preview",
            "perplexity": "sonar",
            "deepseek": "deepseek-chat",
            "venice": "openai-gpt-52",
            "nanogpt": "nanogpt/gpt-4o-mini",
            "ollama": "llama3.3:70b"
        }

        # Group models by provider (skip aliases - they're for programmatic use)
        models_by_provider: Dict[str, list] = {}
        for model_name, info in cls.MODELS.items():
            # Skip alias entries - these are for Qubes to use abbreviated names
            if "alias_for" in info:
                continue
            provider = info["provider"]
            if provider not in models_by_provider:
                models_by_provider[provider] = []
            models_by_provider[provider].append({
                "value": model_name,
                "label": cls._format_model_label(model_name, info),
                "description": info.get("description", "")
            })

        # Build provider list in order
        providers = [
            {"value": p, "label": provider_labels.get(p, p.title())}
            for p in provider_order
            if p in models_by_provider
        ]

        return {
            "providers": providers,
            "models": models_by_provider,
            "defaults": defaults
        }

    @classmethod
    def _format_model_label(cls, model_id: str, info: Dict[str, Any]) -> str:
        """Generate human-readable label from model ID."""
        # Model display name mappings
        label_map = {
            # OpenAI
            "gpt-5.2": "GPT-5.2",  # No trailing space
            "gpt-5.2-chat-latest": "GPT-5.2 Instant",
            "gpt-5.2-codex": "GPT-5.2 Codex",
            "gpt-5.1": "GPT-5.1",
            "gpt-5.1-chat-latest": "GPT-5.1 Instant",
            "gpt-5-turbo": "GPT-5 Turbo",
            "gpt-5": "GPT-5",
            "gpt-5-mini": "GPT-5 Mini",
            "gpt-4.1": "GPT-4.1",
            "gpt-4.1-mini": "GPT-4.1 Mini",
            "o4": "GPT-O4",
            "o4-mini": "GPT-O4 Mini",
            "o3-mini": "GPT-O3 Mini",
            "o1": "GPT-O1",
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            # Anthropic
            "claude-sonnet-4-5-20250929": "Claude Sonnet 4.5",
            "claude-opus-4-1-20250805": "Claude Opus 4.1",
            "claude-opus-4-20250514": "Claude Opus 4",
            "claude-sonnet-4-20250514": "Claude Sonnet 4",
            "claude-3-7-sonnet-20250219": "Claude 3.7 Sonnet",
            "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
            "claude-3-haiku-20240307": "Claude 3 Haiku",
            # Google
            "gemini-3-pro-preview": "Gemini 3 Pro",
            "gemini-3-flash-preview": "Gemini 3 Flash",
            "gemini-3-pro-image-preview": "Gemini 3 Pro Vision",
            "gemini-2.5-pro": "Gemini 2.5 Pro",
            "gemini-2.5-flash": "Gemini 2.5 Flash",
            "gemini-2.5-flash-preview-09-2025": "Gemini 2.5 Flash Preview",
            "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
            "gemini-2.0-flash": "Gemini 2.0 Flash",
            "gemini-1.5-pro": "Gemini 1.5 Pro",
            # Perplexity
            "sonar": "Sonar (Fast)",
            "sonar-pro": "Sonar Pro",
            "sonar-reasoning": "Sonar Reasoning",
            "sonar-reasoning-pro": "Sonar Reasoning Pro",
            "sonar-deep-research": "Sonar Deep Research",
            # DeepSeek
            "deepseek-chat": "DeepSeek Chat (V3.2)",
            "deepseek-reasoner": "DeepSeek Reasoner (R1)",
            # Venice
            "venice-uncensored": "Venice Uncensored",
            "llama-3.3-70b": "Llama 3.3 70B",
            "llama-3.2-3b": "Llama 3.2 3B",
            "qwen3-235b-a22b-instruct-2507": "Qwen3 235B Instruct",
            "qwen3-235b-a22b-thinking-2507": "Qwen3 235B Thinking",
            "qwen3-next-80b": "Qwen3 Next 80B",
            "qwen3-coder-480b-a35b-instruct": "Qwen3 Coder 480B",
            "qwen3-4b": "Venice Small (Fast)",
            "mistral-31-24b": "Venice Medium",
            "claude-opus-45": "Claude Opus 4.5 (Venice)",
            "openai-gpt-52": "GPT-5.2 (Venice)",
            "openai-gpt-oss-120b": "GPT OSS 120B (Venice)",
            "venice/gemini-3-pro": "Gemini 3 Pro (Venice)",
            "venice/gemini-3-flash": "Gemini 3 Flash (Venice)",
            "grok-41-fast": "Grok 4.1 Fast",
            "grok-code-fast-1": "Grok Code Fast 1",
            "zai-org-glm-4.7": "GLM 4.7",
            "kimi-k2-thinking": "Kimi K2 Thinking",
            "minimax-m21": "MiniMax M2.1",
            "deepseek-v3.2": "DeepSeek V3.2",
            "google-gemma-3-27b-it": "Gemma 3 27B",
            "hermes-3-llama-3.1-405b": "Hermes 3 405B",
            # "dolphin-2.9.3-mistral-7b" removed - legacy alias, use venice-uncensored
            # Ollama
            "llama3.3:70b": "Llama 3.3 70B",
            "llama3.2": "Llama 3.2",
            "llama3.2:1b": "Llama 3.2 1B",
            "llama3.2:3b": "Llama 3.2 3B",
            "llama3.2-vision:11b": "Llama 3.2 Vision 11B",
            "llama3.2-vision:90b": "Llama 3.2 Vision 90B",
            "qwen3:235b": "Qwen 3 235B",
            "qwen3:30b": "Qwen 3 30B",
            "qwen2.5:7b": "Qwen 2.5 7B",
            "deepseek-r1:8b": "DeepSeek R1 8B (Local)",
            "phi4:14b": "Phi 4 14B",
            "gemma2:9b": "Gemma 2 9B",
            "mistral:7b": "Mistral 7B",
            "codellama:7b": "CodeLlama 7B",
            # NanoGPT
            "nanogpt/gpt-4o": "GPT-4o (NanoGPT)",
            "nanogpt/gpt-4o-mini": "GPT-4o Mini (NanoGPT)",
            "nanogpt/claude-3-5-sonnet": "Claude 3.5 Sonnet (NanoGPT)",
            "nanogpt/claude-3-haiku": "Claude 3 Haiku (NanoGPT)",
            "nanogpt/llama-3.1-70b": "Llama 3.1 70B (NanoGPT)",
            "nanogpt/llama-3.1-8b": "Llama 3.1 8B (NanoGPT)",
            "nanogpt/mistral-large": "Mistral Large (NanoGPT)",
            "nanogpt/mixtral-8x7b": "Mixtral 8x7B (NanoGPT)",
        }

        if model_id in label_map:
            return label_map[model_id]

        # Fallback: use model_id as-is
        return model_id
