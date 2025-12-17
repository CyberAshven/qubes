"""
Tests for Settings Management (Phase 8)

Tests global and per-Qube settings management.
From docs/13_Implementation_Phases.md Phase 8
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from config import GlobalSettings, QubeSettings, SettingsManager


class TestGlobalSettings:
    """Test GlobalSettings dataclass"""

    def test_default_global_settings(self):
        """Test default global settings values"""
        settings = GlobalSettings()

        assert settings.default_ai_model == "claude-sonnet-4.5"
        assert settings.default_voice_model == "openai:alloy"
        assert settings.max_session_blocks == 50
        assert settings.network_mode == "p2p"
        assert settings.tts_enabled is True
        assert settings.log_level == "INFO"

    def test_custom_global_settings(self):
        """Test custom global settings"""
        settings = GlobalSettings(
            default_ai_model="gpt-5",
            max_session_blocks=100,
            monthly_budget_usd=50.0
        )

        assert settings.default_ai_model == "gpt-5"
        assert settings.max_session_blocks == 100
        assert settings.monthly_budget_usd == 50.0


class TestQubeSettings:
    """Test QubeSettings dataclass"""

    def test_default_qube_settings(self):
        """Test default Qube settings values"""
        settings = QubeSettings()

        assert settings.ai_model is None  # Not overriding
        assert settings.voice_model is None
        assert settings.auto_anchor_enabled is True
        assert settings.response_style == "balanced"
        assert settings.trust_profile == "balanced"
        assert settings.web_search_enabled is True

    def test_custom_qube_settings(self):
        """Test custom Qube settings"""
        settings = QubeSettings(
            ai_model="gpt-5-mini",
            response_style="concise",
            trust_profile="analytical"
        )

        assert settings.ai_model == "gpt-5-mini"
        assert settings.response_style == "concise"
        assert settings.trust_profile == "analytical"


class TestSettingsManager:
    """Test SettingsManager class"""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def settings_manager(self, temp_config_dir):
        """Create test settings manager"""
        return SettingsManager(config_dir=temp_config_dir)

    def test_settings_manager_initialization(self, temp_config_dir):
        """Test settings manager initialization"""
        manager = SettingsManager(config_dir=temp_config_dir)

        assert manager.config_dir == temp_config_dir
        # Directories are created on init
        assert manager.qube_settings_dir.exists()
        # Settings file is created when first loaded
        assert not manager.global_settings_file.exists()

        # Load settings to trigger file creation
        settings = manager.load_global_settings()
        assert manager.global_settings_file.exists()
        assert isinstance(settings, GlobalSettings)

    def test_load_global_settings_creates_default(self, settings_manager):
        """Test loading global settings creates defaults if not exist"""
        settings = settings_manager.load_global_settings()

        assert isinstance(settings, GlobalSettings)
        assert settings.default_ai_model == "claude-sonnet-4.5"

        # File should have been created
        assert settings_manager.global_settings_file.exists()

    def test_save_and_load_global_settings(self, settings_manager):
        """Test saving and loading global settings"""
        # Create custom settings
        settings = GlobalSettings(
            default_ai_model="gpt-5",
            max_session_blocks=75,
            monthly_budget_usd=200.0
        )

        # Save
        settings_manager.save_global_settings(settings)

        # Load
        loaded_settings = settings_manager.load_global_settings()

        assert loaded_settings.default_ai_model == "gpt-5"
        assert loaded_settings.max_session_blocks == 75
        assert loaded_settings.monthly_budget_usd == 200.0

    def test_load_qube_settings_creates_default(self, settings_manager):
        """Test loading Qube settings creates defaults if not exist"""
        qube_id = "test_qube_123"

        settings = settings_manager.load_qube_settings(qube_id)

        assert isinstance(settings, QubeSettings)
        assert settings.response_style == "balanced"

        # File should have been created
        settings_file = settings_manager.qube_settings_dir / f"{qube_id}.yaml"
        assert settings_file.exists()

    def test_save_and_load_qube_settings(self, settings_manager):
        """Test saving and loading Qube settings"""
        qube_id = "test_qube_456"

        # Create custom settings
        settings = QubeSettings(
            ai_model="claude-opus-4.1",
            response_style="detailed",
            trust_profile="social"
        )

        # Save
        settings_manager.save_qube_settings(qube_id, settings)

        # Load
        loaded_settings = settings_manager.load_qube_settings(qube_id)

        assert loaded_settings.ai_model == "claude-opus-4.1"
        assert loaded_settings.response_style == "detailed"
        assert loaded_settings.trust_profile == "social"

    def test_get_effective_settings(self, settings_manager):
        """Test getting effective settings (global + overrides)"""
        # Set global settings
        global_settings = GlobalSettings(
            default_ai_model="claude-sonnet-4.5",
            max_session_blocks=50
        )
        settings_manager.save_global_settings(global_settings)

        # Set Qube-specific overrides
        qube_id = "test_qube_789"
        qube_settings = QubeSettings(
            ai_model="gpt-5",  # Override
            max_session_blocks=100  # Override
        )
        settings_manager.save_qube_settings(qube_id, qube_settings)

        # Get effective settings
        effective = settings_manager.get_effective_settings(qube_id)

        # Overrides should apply
        assert effective["ai_model"] == "gpt-5"
        assert effective["max_session_blocks"] == 100

        # Non-overridden values should come from global
        assert effective["default_voice_model"] == "openai:alloy"

    def test_update_global_setting(self, settings_manager):
        """Test updating a single global setting"""
        settings_manager.update_global_setting("default_ai_model", "gpt-5-mini")

        loaded_settings = settings_manager.load_global_settings()
        assert loaded_settings.default_ai_model == "gpt-5-mini"

    def test_update_qube_setting(self, settings_manager):
        """Test updating a single Qube setting"""
        qube_id = "test_qube_xyz"

        settings_manager.update_qube_setting(qube_id, "response_style", "concise")

        loaded_settings = settings_manager.load_qube_settings(qube_id)
        assert loaded_settings.response_style == "concise"

    def test_reset_global_settings(self, settings_manager):
        """Test resetting global settings to defaults"""
        # Modify settings
        settings_manager.update_global_setting("default_ai_model", "custom-model")

        # Reset
        settings_manager.reset_global_settings()

        # Should be back to defaults
        loaded_settings = settings_manager.load_global_settings()
        assert loaded_settings.default_ai_model == "claude-sonnet-4.5"

    def test_reset_qube_settings(self, settings_manager):
        """Test resetting Qube settings to defaults"""
        qube_id = "test_qube_reset"

        # Modify settings
        settings_manager.update_qube_setting(qube_id, "response_style", "detailed")

        # Reset
        settings_manager.reset_qube_settings(qube_id)

        # Should be back to defaults
        loaded_settings = settings_manager.load_qube_settings(qube_id)
        assert loaded_settings.response_style == "balanced"

    def test_export_import_settings(self, settings_manager, temp_config_dir):
        """Test exporting and importing settings"""
        # Create some settings
        global_settings = GlobalSettings(default_ai_model="gpt-5")
        settings_manager.save_global_settings(global_settings)

        qube_settings = QubeSettings(response_style="concise")
        settings_manager.save_qube_settings("qube_export_test", qube_settings)

        # Export
        export_file = temp_config_dir / "export.yaml"
        settings_manager.export_settings(export_file)

        assert export_file.exists()

        # Create new settings manager
        new_config_dir = temp_config_dir / "new_config"
        new_config_dir.mkdir()
        new_manager = SettingsManager(config_dir=new_config_dir)

        # Import
        new_manager.import_settings(export_file)

        # Verify
        imported_global = new_manager.load_global_settings()
        assert imported_global.default_ai_model == "gpt-5"

        imported_qube = new_manager.load_qube_settings("qube_export_test")
        assert imported_qube.response_style == "concise"
