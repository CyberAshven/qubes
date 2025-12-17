"""
AI Integration Tests

Tests for AI model providers, tool registry, and reasoner.
"""

import pytest
from pathlib import Path

from ai import ModelRegistry, QubeReasoner, ToolRegistry, register_default_tools
from core.qube import Qube
from core.exceptions import AIError
from utils.logging import configure_logging


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary data directory"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    yield data_dir


@pytest.fixture
def qube(test_data_dir):
    """Create test Qube"""
    configure_logging(log_level="INFO", console_output=False)

    qube = Qube.create_new(
        qube_name="AITestQube",
        creator="alice",
        genesis_prompt="You are a helpful AI assistant for testing.",
        ai_model="gpt-4o-mini",
        voice_model="elevenlabs-test",
        data_dir=test_data_dir,
        user_name="test_user"
    )

    yield qube
    qube.close()


def test_model_registry():
    """Test ModelRegistry lists models correctly"""
    # List all models
    all_models = ModelRegistry.list_models()
    assert len(all_models) > 0
    assert "gpt-4o" in all_models
    assert "claude-sonnet-4-5-20250929" in all_models
    assert "gemini-2.0-flash" in all_models

    # List OpenAI models
    openai_models = ModelRegistry.list_models(provider="openai")
    assert all(m["provider"] == "openai" for m in openai_models.values())

    # List Anthropic models
    anthropic_models = ModelRegistry.list_models(provider="anthropic")
    assert all(m["provider"] == "anthropic" for m in anthropic_models.values())

    # Get providers
    providers = ModelRegistry.get_providers()
    assert "openai" in providers
    assert "anthropic" in providers
    assert "google" in providers
    assert "perplexity" in providers
    assert "ollama" in providers


def test_model_registry_get_model_info():
    """Test getting model metadata"""
    info = ModelRegistry.get_model_info("gpt-4o")
    assert info is not None
    assert info["provider"] == "openai"
    assert "description" in info

    # Unknown model
    assert ModelRegistry.get_model_info("fake-model") is None


def test_model_registry_invalid_model():
    """Test error handling for invalid model"""
    with pytest.raises(AIError) as exc_info:
        ModelRegistry.get_model("nonexistent-model", "fake-key")

    assert "Unknown model" in str(exc_info.value)


def test_tool_registry(qube):
    """Test tool registration and retrieval"""
    registry = ToolRegistry(qube)
    register_default_tools(registry)

    # Check default tools registered
    assert len(registry.tools) > 0
    assert "web_search" in registry.tools
    assert "generate_image" in registry.tools
    assert "search_memory" in registry.tools
    # Note: send_message_to_human is NOT a tool - messages are handled directly by AI response

    # List tools
    tool_names = registry.list_tools()
    assert "web_search" in tool_names

    # Get tool
    web_search = registry.get_tool("web_search")
    assert web_search is not None
    assert web_search.name == "web_search"
    assert web_search.description != ""


def test_tool_format_conversion(qube):
    """Test tool format conversion for different providers"""
    registry = ToolRegistry(qube)
    register_default_tools(registry)

    # OpenAI format
    openai_tools = registry.get_tools_for_model("openai")
    assert len(openai_tools) > 0
    assert openai_tools[0]["type"] == "function"
    assert "function" in openai_tools[0]

    # Anthropic format
    anthropic_tools = registry.get_tools_for_model("anthropic")
    assert len(anthropic_tools) > 0
    assert "name" in anthropic_tools[0]
    assert "input_schema" in anthropic_tools[0]

    # Google format
    google_tools = registry.get_tools_for_model("google")
    assert len(google_tools) > 0
    assert "function_declarations" in google_tools[0]


def test_reasoner_initialization(qube):
    """Test QubeReasoner initialization"""
    reasoner = QubeReasoner(qube)

    assert reasoner.qube == qube
    assert reasoner.model is None  # Not loaded until process_input
    assert reasoner.tool_registry is None  # Not set until manually assigned

    # Set tool registry
    registry = ToolRegistry(qube)
    register_default_tools(registry)
    reasoner.set_tool_registry(registry)

    assert reasoner.tool_registry is not None
    assert len(reasoner.tool_registry.tools) > 0


def test_qube_ai_initialization(qube):
    """Test Qube AI initialization"""
    # Initially not initialized
    assert qube.reasoner is None
    assert qube.tool_registry is None

    # Initialize AI (with fake keys for testing)
    qube.init_ai({
        "openai": "fake-key-for-testing",
        "anthropic": "fake-key-for-testing"
    })

    # Check initialized
    assert qube.reasoner is not None
    assert qube.tool_registry is not None
    assert len(qube.tool_registry.tools) > 0
    assert qube.api_keys["openai"] == "fake-key-for-testing"


@pytest.mark.asyncio
async def test_memory_search_tool(qube):
    """Test memory search tool execution"""
    # Initialize AI
    qube.init_ai({"openai": "fake-key"})

    # Add some messages to search
    qube.start_session()
    qube.add_message(
        message_type="qube_to_human",
        recipient_id="alice",
        message_body="Hello, I am a helpful AI assistant.",
        conversation_id="test",
        temporary=True
    )
    qube.add_message(
        message_type="qube_to_human",
        recipient_id="alice",
        message_body="I can help you with many tasks.",
        conversation_id="test",
        temporary=True
    )

    # Anchor to make them permanent
    qube.anchor_session()

    # Search memory
    result = await qube.tool_registry.execute_tool(
        "search_memory",
        {"query": "helpful", "limit": 5},
        record_blocks=False
    )

    assert result["success"] is True
    assert result["count"] >= 1  # Should find at least one match

    # Verify results contain blocks (content will be encrypted for permanent blocks)
    assert len(result["results"]) >= 1
    assert "block_number" in result["results"][0]
    assert "block_type" in result["results"][0]
    # Note: MESSAGE blocks are encrypted when permanent, so we can't search plaintext


def test_qube_process_message_not_initialized(qube):
    """Test error when processing message without AI initialization"""
    import asyncio

    with pytest.raises(Exception) as exc_info:
        asyncio.run(qube.process_message("Hello"))

    assert "AI not initialized" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
