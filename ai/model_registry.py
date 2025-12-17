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
    DeepSeekModel
)
from core.exceptions import AIError
from utils.logging import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """
    Registry of available AI models (Updated: 2025)

    Latest models across 5 providers with support for reasoning,
    vision, and extended context windows.
    """

    MODELS: Dict[str, Dict[str, Any]] = {
        # OpenAI - Latest models (2025)
        "gpt-5-turbo": {"provider": "openai", "class": OpenAIModel, "description": "GPT-5 Turbo (2025), fast and efficient"},
        "gpt-5": {"provider": "openai", "class": OpenAIModel, "description": "Latest flagship (Aug 2025), SOTA", "temperature_fixed": 1.0},
        "gpt-5-mini": {"provider": "openai", "class": OpenAIModel, "description": "Balanced performance/cost"},
        "gpt-5-nano": {"provider": "openai", "class": OpenAIModel, "description": "Lightweight, fast"},
        "gpt-5-codex": {"provider": "openai", "class": OpenAIModel, "description": "Code-specialized (Sep 2025)"},
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

        # Google - Gemini 2.5 generation (2025)
        "gemini-2.5-pro": {"provider": "google", "class": GoogleModel, "description": "Latest, thinking model"},
        "gemini-2.5-flash": {"provider": "google", "class": GoogleModel, "description": "Fast, Jun 2025"},
        "gemini-2.5-flash-lite": {"provider": "google", "class": GoogleModel, "description": "Speed optimized"},
        "gemini-2.0-flash": {"provider": "google", "class": GoogleModel, "description": "Default (Jan 2025)"},
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
            model = model_class(model_name=model_name, api_key=api_key, **kwargs)
            logger.info(
                "model_loaded",
                model=model_name,
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
