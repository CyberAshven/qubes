"""
Integration test for UserOrchestrator API key management

Tests the integration of SecureSettingsManager with UserOrchestrator.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from orchestrator.user_orchestrator import UserOrchestrator
from config import APIKeys


class TestOrchestratorAPIKeys:
    """Test UserOrchestrator API key management"""

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
        orch = UserOrchestrator(user_id="test_user", data_dir=temp_data_dir)
        orch.set_master_key("test_password")
        return orch

    def test_orchestrator_has_secure_settings(self, orchestrator):
        """Test that orchestrator has secure settings manager"""
        assert orchestrator.secure_settings is not None
        assert orchestrator.secure_settings.user_data_dir == orchestrator.data_dir

    def test_set_master_key_initializes_secure_settings(self, temp_data_dir):
        """Test that set_master_key also sets password for secure settings"""
        orch = UserOrchestrator(user_id="test_user", data_dir=temp_data_dir)

        # Secure settings should not have password yet
        assert orch.secure_settings._master_password is None

        # Set master key
        orch.set_master_key("my_password")

        # Should also set password for secure settings
        assert orch.secure_settings._master_password == "my_password"

    def test_save_and_get_api_keys(self, orchestrator):
        """Test saving and retrieving API keys through orchestrator"""
        # Save API keys
        api_keys = APIKeys(
            openai="sk-test-openai",
            anthropic="sk-ant-test"
        )
        orchestrator.save_api_keys(api_keys)

        # Retrieve API keys
        retrieved = orchestrator.get_api_keys()

        assert retrieved.openai == "sk-test-openai"
        assert retrieved.anthropic == "sk-ant-test"

    def test_update_single_api_key(self, orchestrator):
        """Test updating a single API key"""
        # Save initial keys
        api_keys = APIKeys(openai="sk-old-key")
        orchestrator.save_api_keys(api_keys)

        # Update OpenAI key
        orchestrator.update_api_key("openai", "sk-new-key")

        # Verify update
        retrieved = orchestrator.get_api_keys()
        assert retrieved.openai == "sk-new-key"

    def test_delete_api_key(self, orchestrator):
        """Test deleting an API key"""
        # Save keys
        api_keys = APIKeys(
            openai="sk-test",
            anthropic="sk-ant-test"
        )
        orchestrator.save_api_keys(api_keys)

        # Delete OpenAI key
        orchestrator.delete_api_key("openai")

        # Verify deletion
        retrieved = orchestrator.get_api_keys()
        assert retrieved.openai is None
        assert retrieved.anthropic == "sk-ant-test"  # Still exists

    def test_list_configured_providers(self, orchestrator):
        """Test listing configured providers"""
        # No keys initially
        assert orchestrator.list_configured_providers() == []

        # Add some keys
        api_keys = APIKeys(
            openai="sk-test",
            google="google-test"
        )
        orchestrator.save_api_keys(api_keys)

        # List providers
        providers = orchestrator.list_configured_providers()
        assert "openai" in providers
        assert "google" in providers
        assert len(providers) == 2

    def test_has_api_keys_configured(self, orchestrator):
        """Test checking if API keys are configured"""
        # No keys initially
        assert orchestrator.has_api_keys_configured() is False

        # Add keys
        api_keys = APIKeys(openai="sk-test")
        orchestrator.save_api_keys(api_keys)

        # Should return True
        assert orchestrator.has_api_keys_configured() is True

    def test_get_api_keys_helper_returns_dict(self, orchestrator):
        """Test _get_api_keys helper returns dictionary"""
        # Save keys
        api_keys = APIKeys(
            openai="sk-test",
            anthropic="sk-ant-test"
        )
        orchestrator.save_api_keys(api_keys)

        # Get API keys via helper (used internally by load_qube)
        api_keys_dict = orchestrator._get_api_keys()

        # Should be a dictionary
        assert isinstance(api_keys_dict, dict)
        assert api_keys_dict["openai"] == "sk-test"
        assert api_keys_dict["anthropic"] == "sk-ant-test"

    def test_get_api_keys_falls_back_to_env(self, temp_data_dir, monkeypatch):
        """Test that _get_api_keys falls back to environment variables"""
        # Set environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-openai")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-anthropic")

        # Create orchestrator without secure keys
        orch = UserOrchestrator(user_id="test_user", data_dir=temp_data_dir)
        orch.set_master_key("test_password")

        # Should fall back to environment
        api_keys = orch._get_api_keys()

        assert api_keys["openai"] == "sk-env-openai"
        assert api_keys["anthropic"] == "sk-env-anthropic"

    def test_secure_keys_take_precedence_over_env(self, temp_data_dir, monkeypatch):
        """Test that secure settings take precedence over environment variables"""
        # Set environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")

        # Create orchestrator and save secure keys
        orch = UserOrchestrator(user_id="test_user", data_dir=temp_data_dir)
        orch.set_master_key("test_password")

        api_keys = APIKeys(openai="sk-secure-key")
        orch.save_api_keys(api_keys)

        # Should use secure key, not env
        loaded_keys = orch._get_api_keys()

        assert loaded_keys["openai"] == "sk-secure-key"

    @pytest.mark.asyncio
    async def test_validate_api_key_through_orchestrator(self, orchestrator):
        """Test API key validation through orchestrator"""
        # Test with invalid key (will fail but tests the flow)
        result = await orchestrator.validate_api_key("openai", "sk-invalid")

        # Should return validation result structure
        assert "valid" in result
        assert "message" in result
        assert isinstance(result["valid"], bool)
