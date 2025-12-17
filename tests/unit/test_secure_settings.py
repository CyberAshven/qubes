"""
Tests for SecureSettingsManager (API Key Management)

Tests encrypted storage and validation of API keys.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from config import APIKeys, SecureSettingsManager
from core.exceptions import EncryptionError, DecryptionError


class TestAPIKeys:
    """Test APIKeys dataclass"""

    def test_default_api_keys(self):
        """Test default API keys (all None)"""
        keys = APIKeys()

        assert keys.openai is None
        assert keys.anthropic is None
        assert keys.google is None
        assert keys.deepseek is None
        assert keys.perplexity is None
        assert keys.pinata_jwt is None
        assert keys.elevenlabs is None
        assert keys.deepgram is None

    def test_custom_api_keys(self):
        """Test custom API keys"""
        keys = APIKeys(
            openai="sk-test-openai",
            anthropic="sk-ant-test",
            google="test-google-key"
        )

        assert keys.openai == "sk-test-openai"
        assert keys.anthropic == "sk-ant-test"
        assert keys.google == "test-google-key"
        assert keys.deepseek is None  # Not set

    def test_to_dict_excludes_none(self):
        """Test to_dict() excludes None values"""
        keys = APIKeys(
            openai="sk-test",
            anthropic=None,
            google="google-test"
        )

        keys_dict = keys.to_dict()

        assert "openai" in keys_dict
        assert "google" in keys_dict
        assert "anthropic" not in keys_dict  # Excluded because None

    def test_is_empty(self):
        """Test is_empty() method"""
        # Empty keys
        empty_keys = APIKeys()
        assert empty_keys.is_empty() is True

        # Non-empty keys
        non_empty_keys = APIKeys(openai="sk-test")
        assert non_empty_keys.is_empty() is False


class TestSecureSettingsManager:
    """Test SecureSettingsManager class"""

    @pytest.fixture
    def temp_user_dir(self):
        """Create temporary user directory"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def secure_manager(self, temp_user_dir):
        """Create test secure settings manager"""
        manager = SecureSettingsManager(temp_user_dir, master_password="test_password")
        return manager

    def test_initialization(self, temp_user_dir):
        """Test secure settings manager initialization"""
        manager = SecureSettingsManager(temp_user_dir, master_password="test_pass")

        assert manager.user_data_dir == temp_user_dir
        assert manager.user_data_dir.exists()
        assert manager.api_keys_file == temp_user_dir / "api_keys.enc"
        assert manager.salt_file == temp_user_dir / "salt.bin"

    def test_set_master_password(self, temp_user_dir):
        """Test setting master password"""
        manager = SecureSettingsManager(temp_user_dir)
        assert manager._master_password is None

        manager.set_master_password("my_password")
        assert manager._master_password == "my_password"

    def test_save_and_load_api_keys(self, secure_manager):
        """Test saving and loading encrypted API keys"""
        # Create test API keys
        api_keys = APIKeys(
            openai="sk-test-openai-key",
            anthropic="sk-ant-test-key",
            google="google-test-key"
        )

        # Save
        secure_manager.save_api_keys(api_keys)

        # Verify encrypted file exists
        assert secure_manager.api_keys_file.exists()

        # Load
        loaded_keys = secure_manager.load_api_keys()

        # Verify
        assert loaded_keys.openai == "sk-test-openai-key"
        assert loaded_keys.anthropic == "sk-ant-test-key"
        assert loaded_keys.google == "google-test-key"
        assert loaded_keys.deepseek is None

    def test_load_nonexistent_keys_returns_empty(self, secure_manager):
        """Test loading API keys when file doesn't exist"""
        # File shouldn't exist yet
        assert not secure_manager.api_keys_file.exists()

        # Should return empty APIKeys
        loaded_keys = secure_manager.load_api_keys()

        assert loaded_keys.is_empty() is True

    def test_encryption_requires_master_password(self, temp_user_dir):
        """Test that encryption requires master password"""
        manager = SecureSettingsManager(temp_user_dir)  # No password

        api_keys = APIKeys(openai="sk-test")

        # Should raise EncryptionError
        with pytest.raises(EncryptionError) as exc_info:
            manager.save_api_keys(api_keys)

        # Check that the error is about encryption failure
        # The actual "Master password not set" is in the cause
        assert "Failed to save encrypted API keys" in str(exc_info.value) or "Master password not set" in str(exc_info.value)

    def test_wrong_password_fails_decryption(self, temp_user_dir):
        """Test that wrong master password fails decryption"""
        # Save with one password
        manager1 = SecureSettingsManager(temp_user_dir, master_password="correct_password")
        api_keys = APIKeys(openai="sk-test")
        manager1.save_api_keys(api_keys)

        # Try to load with wrong password
        manager2 = SecureSettingsManager(temp_user_dir, master_password="wrong_password")

        with pytest.raises(DecryptionError) as exc_info:
            manager2.load_api_keys()

        assert "Failed to decrypt" in str(exc_info.value)

    def test_update_api_key(self, secure_manager):
        """Test updating a single API key"""
        # Update OpenAI key
        secure_manager.update_api_key("openai", "sk-new-openai-key")

        # Verify
        loaded_keys = secure_manager.load_api_keys()
        assert loaded_keys.openai == "sk-new-openai-key"

        # Update Anthropic key
        secure_manager.update_api_key("anthropic", "sk-ant-new-key")

        # Verify both keys exist
        loaded_keys = secure_manager.load_api_keys()
        assert loaded_keys.openai == "sk-new-openai-key"
        assert loaded_keys.anthropic == "sk-ant-new-key"

    def test_update_invalid_provider_raises_error(self, secure_manager):
        """Test updating invalid provider raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            secure_manager.update_api_key("invalid_provider", "test-key")

        assert "Invalid provider" in str(exc_info.value)

    def test_get_api_key(self, secure_manager):
        """Test getting a single API key"""
        # Save keys
        api_keys = APIKeys(
            openai="sk-openai-test",
            anthropic="sk-ant-test"
        )
        secure_manager.save_api_keys(api_keys)

        # Get individual keys
        openai_key = secure_manager.get_api_key("openai")
        anthropic_key = secure_manager.get_api_key("anthropic")
        google_key = secure_manager.get_api_key("google")

        assert openai_key == "sk-openai-test"
        assert anthropic_key == "sk-ant-test"
        assert google_key is None  # Not set

    def test_delete_api_key(self, secure_manager):
        """Test deleting a single API key"""
        # Save keys
        api_keys = APIKeys(
            openai="sk-openai-test",
            anthropic="sk-ant-test"
        )
        secure_manager.save_api_keys(api_keys)

        # Delete OpenAI key
        secure_manager.delete_api_key("openai")

        # Verify
        loaded_keys = secure_manager.load_api_keys()
        assert loaded_keys.openai is None
        assert loaded_keys.anthropic == "sk-ant-test"  # Still exists

    def test_clear_all_api_keys(self, secure_manager):
        """Test clearing all API keys"""
        # Save keys
        api_keys = APIKeys(
            openai="sk-openai-test",
            anthropic="sk-ant-test"
        )
        secure_manager.save_api_keys(api_keys)

        assert secure_manager.api_keys_file.exists()

        # Clear all
        secure_manager.clear_all_api_keys()

        # Verify file deleted
        assert not secure_manager.api_keys_file.exists()

    def test_has_api_keys(self, secure_manager):
        """Test has_api_keys() method"""
        # No keys initially
        assert secure_manager.has_api_keys() is False

        # Add keys
        api_keys = APIKeys(openai="sk-test")
        secure_manager.save_api_keys(api_keys)

        # Should return True
        assert secure_manager.has_api_keys() is True

        # Clear keys
        secure_manager.clear_all_api_keys()

        # Should return False
        assert secure_manager.has_api_keys() is False

    def test_list_configured_providers(self, secure_manager):
        """Test list_configured_providers() method"""
        # No keys initially
        providers = secure_manager.list_configured_providers()
        assert providers == []

        # Add some keys
        api_keys = APIKeys(
            openai="sk-openai-test",
            google="google-test",
            pinata_jwt="jwt-test"
        )
        secure_manager.save_api_keys(api_keys)

        # List providers
        providers = secure_manager.list_configured_providers()

        assert "openai" in providers
        assert "google" in providers
        assert "pinata_jwt" in providers
        assert "anthropic" not in providers  # Not set

    def test_encryption_creates_salt_file(self, secure_manager):
        """Test that encryption creates salt file for new users"""
        # Save keys
        api_keys = APIKeys(openai="sk-test")
        secure_manager.save_api_keys(api_keys)

        # Verify salt file created
        assert secure_manager.salt_file.exists()

        # Verify iterations file created (600K for new users)
        assert secure_manager.iterations_file.exists()
        iterations = int(secure_manager.iterations_file.read_text().strip())
        assert iterations == 600000

    def test_encryption_key_caching(self, secure_manager):
        """Test that encryption key is cached for performance"""
        # First derivation
        key1 = secure_manager._derive_encryption_key()

        # Second derivation (should use cache)
        key2 = secure_manager._derive_encryption_key()

        # Should be same object (cached)
        assert key1 is key2

    def test_deterministic_encryption_key(self, temp_user_dir):
        """Test that same password produces same encryption key"""
        # Create manager 1
        manager1 = SecureSettingsManager(temp_user_dir, master_password="password123")
        key1 = manager1._derive_encryption_key()

        # Create manager 2 with same password (reusing salt)
        manager2 = SecureSettingsManager(temp_user_dir, master_password="password123")
        key2 = manager2._derive_encryption_key()

        # Keys should be identical
        assert key1 == key2

    def test_different_passwords_produce_different_keys(self, temp_user_dir):
        """Test that different passwords produce different keys"""
        # Create manager 1
        manager1 = SecureSettingsManager(temp_user_dir, master_password="password1")
        key1 = manager1._derive_encryption_key()

        # Create manager 2 with different password
        manager2 = SecureSettingsManager(temp_user_dir, master_password="password2")
        key2 = manager2._derive_encryption_key()

        # Keys should be different
        assert key1 != key2


class TestAPIKeyValidation:
    """Test API key validation methods"""

    @pytest.fixture
    def secure_manager(self, tmp_path):
        """Create test secure settings manager"""
        manager = SecureSettingsManager(tmp_path, master_password="test_password")
        return manager

    @pytest.mark.asyncio
    async def test_validate_api_key_unsupported_provider(self, secure_manager):
        """Test validation for unsupported provider"""
        result = await secure_manager.validate_api_key("unknown_provider", "test-key")

        assert result["valid"] is False
        assert "not implemented" in result["message"].lower()

    # Note: Real API validation tests would require actual API keys or mocking
    # For now, we test the structure of validation responses

    @pytest.mark.asyncio
    async def test_validate_openai_structure(self, secure_manager):
        """Test OpenAI validation returns correct structure"""
        # This will fail because it's an invalid key, but we can test the structure
        result = await secure_manager.validate_api_key("openai", "sk-invalid-test-key")

        assert "valid" in result
        assert "message" in result
        assert "details" in result
        assert isinstance(result["valid"], bool)
        assert isinstance(result["message"], str)

    @pytest.mark.asyncio
    async def test_validation_handles_network_errors(self, secure_manager):
        """Test that validation handles network errors gracefully"""
        # Use invalid URL format to trigger connection error
        result = await secure_manager.validate_api_key("openai", "")

        assert result["valid"] is False
        assert "error" in result["message"].lower() or "connection" in result["message"].lower()
