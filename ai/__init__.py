"""
AI Integration Layer

Multi-provider AI model support with tool calling and reasoning.

Exports:
    - ModelRegistry: Access to all AI models
    - QubeReasoner: Main reasoning engine
    - ToolRegistry, ToolDefinition: Tool system
    - AIFallbackChain: Multi-tier fallback for reliability
    - CircuitBreakerRegistry: Circuit breaker management
    - AvatarGenerator: AI-powered avatar generation
    - Provider classes: OpenAIModel, AnthropicModel, etc.
"""

from ai.model_registry import ModelRegistry
from ai.reasoner import QubeReasoner
from ai.tools import ToolRegistry, ToolDefinition, register_default_tools
from ai.fallback import AIFallbackChain
from ai.circuit_breakers import CircuitBreakerRegistry
from ai.avatar_generator import AvatarGenerator, generate_qube_avatar
from ai.providers import (
    AIModelInterface,
    ModelResponse,
    OpenAIModel,
    AnthropicModel,
    GoogleModel,
    PerplexityModel,
    OllamaModel,
    DeepSeekModel
)

__all__ = [
    "ModelRegistry",
    "QubeReasoner",
    "ToolRegistry",
    "ToolDefinition",
    "register_default_tools",
    "AIFallbackChain",
    "CircuitBreakerRegistry",
    "AvatarGenerator",
    "generate_qube_avatar",
    "AIModelInterface",
    "ModelResponse",
    "OpenAIModel",
    "AnthropicModel",
    "GoogleModel",
    "PerplexityModel",
    "OllamaModel",
    "DeepSeekModel",
]
