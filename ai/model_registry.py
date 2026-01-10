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
    VeniceModel
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

    MODELS: Dict[str, Dict[str, Any]] = {
        # OpenAI - Latest models (2025-2026)
        "gpt-5.2": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.2 Thinking (Dec 2025), SOTA", "temperature_fixed": 1.0},
        "gpt-5.2-pro": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.2 Pro with xhigh reasoning", "temperature_fixed": 1.0},
        "gpt-5.2-chat-latest": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.2 Instant, fast responses"},
        "gpt-5.2-codex": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.2 Codex, SOTA coding"},
        "gpt-5.1": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.1 Thinking, adaptive reasoning", "temperature_fixed": 1.0},
        "gpt-5.1-chat-latest": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5.1 Instant"},
        "gpt-5-turbo": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5 Turbo, fast and efficient"},
        "gpt-5": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5 flagship (Aug 2025)", "temperature_fixed": 1.0},
        "gpt-5-mini": {"provider": "openai", "class": OpenAIModel, "description": "Balanced performance/cost"},
        "gpt-4.1": {"provider": "openai", "class": OpenAIModel, "description": "1M context"},
        "gpt-4.1-mini": {"provider": "openai", "class": OpenAIModel, "description": "Faster, cheaper"},
        "gpt-4o": {"provider": "openai", "class": OpenAIModel, "description": "Multimodal"},
        "gpt-4o-mini": {"provider": "openai", "class": OpenAIModel, "description": "Replaced 3.5-turbo"},
        "o4": {"provider": "openai", "class": OpenAIModel, "description": "Reasoning model GPT-O4 (2025)", "temperature_fixed": 1.0},
        "o4-mini": {"provider": "openai", "class": OpenAIModel, "description": "Reasoning model (2025)", "temperature_fixed": 1.0},
        "o3-mini": {"provider": "openai", "class": OpenAIModel, "description": "Reasoning model", "temperature_fixed": 1.0},
        "o1": {"provider": "openai", "class": OpenAIModel, "description": "Reasoning model", "temperature_fixed": 1.0},

        # Anthropic - Claude 4 generation (2025)
        "claude-sonnet-4-5-20250929": {"provider": "anthropic", "class": AnthropicModel, "description": "Latest, Sep 2025"},
        "claude-opus-4-1-20250805": {"provider": "anthropic", "class": AnthropicModel, "description": "Aug 2025, best coding"},
        "claude-opus-4-20250514": {"provider": "anthropic", "class": AnthropicModel, "description": "Hybrid thinking mode"},
        "claude-sonnet-4-20250514": {"provider": "anthropic", "class": AnthropicModel, "description": "1M context"},
        "claude-3-7-sonnet-20250219": {"provider": "anthropic", "class": AnthropicModel, "description": "Hybrid reasoning, Feb 2025"},
        "claude-3-5-haiku-20241022": {"provider": "anthropic", "class": AnthropicModel, "description": "Fast"},
        "claude-3-haiku-20240307": {"provider": "anthropic", "class": AnthropicModel, "description": "Legacy"},

        # Google - Gemini 3 and 2.5 generation (2025-2026)
        "gemini-3-pro-preview": {"provider": "google", "class": GoogleModel, "description": "Gemini 3 Pro Preview, best multimodal"},
        "gemini-3-flash-preview": {"provider": "google", "class": GoogleModel, "description": "Gemini 3 Flash Preview, balanced speed/intelligence"},
        "gemini-3-pro-image-preview": {"provider": "google", "class": GoogleModel, "description": "Gemini 3 Pro Image Preview"},
        "gemini-2.5-pro": {"provider": "google", "class": GoogleModel, "description": "SOTA thinking model"},
        "gemini-2.5-flash": {"provider": "google", "class": GoogleModel, "description": "Stable general-purpose"},
        "gemini-2.5-flash-preview-09-2025": {"provider": "google", "class": GoogleModel, "description": "Flash preview (Sep 2025)"},
        "gemini-2.5-flash-lite": {"provider": "google", "class": GoogleModel, "description": "Cost-optimized"},
        "gemini-2.0-flash": {"provider": "google", "class": GoogleModel, "description": "Legacy (Jan 2025)"},
        "gemini-1.5-pro": {"provider": "google", "class": GoogleModel, "description": "Legacy"},

        # Perplexity - Sonar generation (2025)
        "sonar-pro": {"provider": "perplexity", "class": PerplexityModel, "description": "Deep search, more citations"},
        "sonar": {"provider": "perplexity", "class": PerplexityModel, "description": "Fast, based on Llama 3.3"},
        "sonar-reasoning-pro": {"provider": "perplexity", "class": PerplexityModel, "description": "Chain-of-thought"},
        "sonar-reasoning": {"provider": "perplexity", "class": PerplexityModel, "description": "Logical reasoning"},
        "sonar-deep-research": {"provider": "perplexity", "class": PerplexityModel, "description": "Most advanced"},

        # DeepSeek - V3.2 and R1 (2025)
        "deepseek-chat": {"provider": "deepseek", "class": DeepSeekModel, "description": "DeepSeek-V3.2 general chat, 64k context"},
        "deepseek-reasoner": {"provider": "deepseek", "class": DeepSeekModel, "description": "DeepSeek-R1 reasoning (32k CoT, 64k context)"},

        # Venice - Privacy-first AI (2025-2026)
        # Note: Venice uses specific model names - check docs.venice.ai for current list
        # Some models use prompt-based tool calling (injected into system prompt)
        "venice-uncensored": {"provider": "venice", "class": VeniceModel, "description": "Venice Uncensored 1.1 - Dolphin"},
        "llama-3.3-70b": {"provider": "venice", "class": VeniceModel, "description": "Llama 3.3 70B via Venice"},
        "llama-3.2-3b": {"provider": "venice", "class": VeniceModel, "description": "Llama 3.2 3B (fast)"},
        "qwen3-235b-a22b-instruct-2507": {"provider": "venice", "class": VeniceModel, "description": "Qwen3 235B Instruct"},
        "qwen3-235b-a22b-thinking-2507": {"provider": "venice", "class": VeniceModel, "description": "Qwen3 235B Thinking (reasoning)"},
        "qwen3-next-80b": {"provider": "venice", "class": VeniceModel, "description": "Qwen3 Next 80B"},
        "qwen3-coder-480b-a35b-instruct": {"provider": "venice", "class": VeniceModel, "description": "Qwen3 Coder 480B"},
        "qwen3-4b": {"provider": "venice", "class": VeniceModel, "description": "Venice Small (Qwen3 4B)"},
        "mistral-31-24b": {"provider": "venice", "class": VeniceModel, "description": "Venice Medium (Mistral 3.1 24B)"},
        "claude-opus-45": {"provider": "venice", "class": VeniceModel, "description": "Claude Opus 4.5 via Venice"},
        "openai-gpt-52": {"provider": "venice", "class": VeniceModel, "description": "GPT-5.2 via Venice"},
        "openai-gpt-oss-120b": {"provider": "venice", "class": VeniceModel, "description": "OpenAI GPT OSS 120B via Venice"},
        "gemini-3-pro-preview": {"provider": "venice", "class": VeniceModel, "description": "Gemini 3 Pro via Venice"},
        "gemini-3-flash-preview": {"provider": "venice", "class": VeniceModel, "description": "Gemini 3 Flash via Venice"},
        "grok-41-fast": {"provider": "venice", "class": VeniceModel, "description": "Grok 4.1 Fast via Venice"},
        "grok-code-fast-1": {"provider": "venice", "class": VeniceModel, "description": "Grok Code Fast 1 via Venice"},
        "zai-org-glm-4.7": {"provider": "venice", "class": VeniceModel, "description": "GLM 4.7 via Venice"},
        "kimi-k2-thinking": {"provider": "venice", "class": VeniceModel, "description": "Kimi K2 Thinking via Venice"},
        "minimax-m21": {"provider": "venice", "class": VeniceModel, "description": "MiniMax M2.1 via Venice"},
        "deepseek-v3.2": {"provider": "venice", "class": VeniceModel, "description": "DeepSeek V3.2 via Venice"},
        "google-gemma-3-27b-it": {"provider": "venice", "class": VeniceModel, "description": "Gemma 3 27B Instruct via Venice"},
        "hermes-3-llama-3.1-405b": {"provider": "venice", "class": VeniceModel, "description": "Hermes 3 Llama 405B via Venice"},
        # Legacy alias
        "dolphin-2.9.3-mistral-7b": {"provider": "venice", "class": VeniceModel, "description": "Legacy: Use venice-uncensored", "alias_for": "venice-uncensored"},

        # Ollama - Popular local models (2025)
        "llama3.3:70b": {"provider": "ollama", "class": OllamaModel, "description": "Latest Llama"},
        "llama3.2": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 instruction-tuned (1B/3B)"},
        "llama3.2:1b": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 1B lightweight"},
        "llama3.2:3b": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 3B"},
        "llama3.2-vision:11b": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 Vision 11B (multimodal)"},
        "llama3.2-vision:90b": {"provider": "ollama", "class": OllamaModel, "description": "Llama 3.2 Vision 90B (multimodal)"},
        "qwen3:235b": {"provider": "ollama", "class": OllamaModel, "description": "Latest Qwen (Apr 2025)"},
        "qwen3:30b": {"provider": "ollama", "class": OllamaModel, "description": "Small MoE"},
        "qwen2.5:7b": {"provider": "ollama", "class": OllamaModel, "description": "Popular lightweight"},
        "deepseek-r1:8b": {"provider": "ollama", "class": OllamaModel, "description": "Reasoning (local)"},
        "phi4:14b": {"provider": "ollama", "class": OllamaModel, "description": "Microsoft's latest"},
        "gemma2:9b": {"provider": "ollama", "class": OllamaModel, "description": "Google"},
        "mistral:7b": {"provider": "ollama", "class": OllamaModel, "description": "Popular"},
        "codellama:7b": {"provider": "ollama", "class": OllamaModel, "description": "Code-specialized"},
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
            "ollama": "Ollama (Local)"
        }

        # Provider order for UI
        provider_order = ["openai", "anthropic", "google", "perplexity", "deepseek", "venice", "ollama"]

        defaults = {
            "openai": "gpt-5.2",
            "anthropic": "claude-sonnet-4-5-20250929",
            "google": "gemini-3-flash-preview",
            "perplexity": "sonar",
            "deepseek": "deepseek-chat",
            "venice": "openai-gpt-52",
            "ollama": "llama3.3:70b"
        }

        # Group models by provider
        models_by_provider: Dict[str, list] = {}
        for model_name, info in cls.MODELS.items():
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
            "gpt-5.2": "GPT-5.2 (Latest)",
            "gpt-5.2-pro": "GPT-5.2 Pro",
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
            "gemini-3-pro-preview": "Gemini 3 Pro (Latest)",
            "gemini-3-flash-preview": "Gemini 3 Flash",
            "gemini-3-pro-image-preview": "Gemini 3 Pro Image",
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
            "grok-41-fast": "Grok 4.1 Fast",
            "grok-code-fast-1": "Grok Code Fast 1",
            "zai-org-glm-4.7": "GLM 4.7",
            "kimi-k2-thinking": "Kimi K2 Thinking",
            "minimax-m21": "MiniMax M2.1",
            "deepseek-v3.2": "DeepSeek V3.2",
            "google-gemma-3-27b-it": "Gemma 3 27B",
            "hermes-3-llama-3.1-405b": "Hermes 3 405B",
            "dolphin-2.9.3-mistral-7b": "Venice Uncensored",
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
        }

        if model_id in label_map:
            return label_map[model_id]

        # Fallback: use model_id as-is
        return model_id
