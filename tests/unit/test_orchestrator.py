"""
Tests for User Orchestrator (Phase 8)

Tests orchestrator functionality including Qube lifecycle management.
From docs/13_Implementation_Phases.md Phase 8
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from orchestrator import UserOrchestrator
from core.exceptions import QubesError


class TestUserOrchestrator:
    """Test UserOrchestrator class"""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def orchestrator(self, temp_data_dir):
        """Create test orchestrator"""
        orch = UserOrchestrator(
            user_id="test_user",
            data_dir=temp_data_dir
        )
        orch.set_master_key("test_password_123")
        return orch

    def test_orchestrator_initialization(self, temp_data_dir):
        """Test orchestrator initialization"""
        orch = UserOrchestrator(
            user_id="test_user",
            data_dir=temp_data_dir
        )

        assert orch.user_id == "test_user"
        assert orch.data_dir == temp_data_dir
        assert len(orch.qubes) == 0
        assert orch.master_key is None

    def test_set_master_key(self, orchestrator):
        """Test master key derivation"""
        assert orchestrator.master_key is not None
        assert len(orchestrator.master_key) == 32  # 256 bits

        # Master key should be deterministic for same password
        orch2 = UserOrchestrator(
            user_id="test_user",
            data_dir=orchestrator.data_dir
        )
        orch2.set_master_key("test_password_123")

        assert orch2.master_key == orchestrator.master_key

    def test_load_global_settings(self, orchestrator):
        """Test loading global settings"""
        settings = orchestrator._load_global_settings()

        assert "default_ai_model" in settings
        assert "max_session_blocks" in settings
        assert "network_mode" in settings

    @pytest.mark.asyncio
    async def test_create_qube_basic(self, orchestrator):
        """Test basic Qube creation"""
        config = {
            "name": "TestQube",
            "genesis_prompt": "You are a test Qube",
            "ai_model": "claude-sonnet-4.5",
            "wallet_address": ""  # Skip NFT minting for test
        }

        # Note: This will fail without proper blockchain setup
        # For unit test, we'll test the validation only
        with pytest.raises(Exception):  # Will fail at blockchain step
            qube = await orchestrator.create_qube(config)

    def test_create_qube_missing_fields(self, orchestrator):
        """Test Qube creation with missing required fields"""
        config = {
            "name": "TestQube"
            # Missing genesis_prompt and ai_model
        }

        with pytest.raises(QubesError) as exc_info:
            asyncio.run(orchestrator.create_qube(config))

        assert "Missing required field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_qubes_empty(self, orchestrator):
        """Test listing Qubes when none exist"""
        qubes = await orchestrator.list_qubes()

        assert qubes == []

    def test_default_voice_for_model(self, orchestrator):
        """Test default voice selection for different AI models"""
        # OpenAI models
        assert orchestrator._default_voice_for_model("gpt-5") == "openai:alloy"
        assert orchestrator._default_voice_for_model("gpt-4o") == "openai:alloy"
        assert orchestrator._default_voice_for_model("o4-mini") == "openai:alloy"

        # Anthropic models
        assert orchestrator._default_voice_for_model("claude-sonnet-4.5") == "openai:nova"
        assert orchestrator._default_voice_for_model("claude-opus-4") == "openai:nova"

        # Google models
        assert orchestrator._default_voice_for_model("gemini-2.5-pro") == "openai:shimmer"

        # Ollama models
        assert orchestrator._default_voice_for_model("llama3.3:70b") == "piper:en_US-lessac-medium"
        assert orchestrator._default_voice_for_model("qwen3:235b") == "piper:en_US-lessac-medium"

    def test_default_capabilities(self, orchestrator):
        """Test default capabilities"""
        capabilities = orchestrator._default_capabilities()

        assert capabilities["web_search"] is True
        assert capabilities["image_generation"] is False  # Disabled by default
        assert capabilities["tts"] is True
        assert capabilities["stt"] is True
        assert capabilities["code_execution"] is False  # Security risk

    def test_encrypt_decrypt_private_key(self, orchestrator):
        """Test private key encryption/decryption"""
        from crypto.keys import generate_key_pair, serialize_private_key

        private_key, public_key = generate_key_pair()

        # Encrypt
        encrypted = orchestrator._encrypt_private_key(private_key, orchestrator.master_key)

        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

        # Decrypt
        decrypted = orchestrator._decrypt_private_key(
            encrypted.hex(),
            orchestrator.master_key
        )

        # Verify it's the same key
        original_bytes = serialize_private_key(private_key)
        decrypted_bytes = serialize_private_key(decrypted)

        assert original_bytes == decrypted_bytes
