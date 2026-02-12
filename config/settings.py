"""
Settings Management

Global and per-Qube settings management with YAML configuration.
From docs/13_Implementation_Phases.md Phase 8
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GlobalSettings:
    """
    Global user settings

    These settings apply across all Qubes unless overridden.
    """
    # Default AI configuration
    default_ai_model: str = "claude-sonnet-4.5"
    default_voice_model: str = "openai:alloy"
    default_ai_temperature: float = 0.7

    # Memory configuration
    max_session_blocks: int = 50  # Max session blocks before anchoring
    auto_anchor_threshold: int = 100  # Auto-anchor when reaching this many session blocks
    memory_search_limit: int = 10  # Max results for memory search

    # Network configuration
    network_mode: str = "p2p"  # p2p or relay
    p2p_port: int = 4001
    discovery_interval: int = 60  # Seconds between discovery attempts

    # Audio configuration
    tts_enabled: bool = True
    stt_enabled: bool = True
    audio_cache_size_mb: int = 500
    audio_cache_ttl_days: int = 7

    # Cost management
    monthly_budget_usd: float = 100.0
    alert_threshold_percent: int = 80  # Alert when 80% of budget used

    # Security settings
    require_master_password: bool = True
    session_timeout_minutes: int = 60
    auto_lock_enabled: bool = True

    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_to_file: bool = True
    log_file_max_size_mb: int = 10


@dataclass
class QubeSettings:
    """
    Per-Qube settings

    These override global settings for specific Qubes.
    """
    # AI overrides
    ai_model: Optional[str] = None
    voice_model: Optional[str] = None
    ai_temperature: Optional[float] = None

    # Memory overrides
    max_session_blocks: Optional[int] = None
    auto_anchor_enabled: Optional[bool] = True

    # Personality
    response_style: str = "balanced"  # concise, balanced, detailed
    formality_level: str = "casual"  # formal, casual, friendly

    # Capabilities
    web_search_enabled: bool = True
    image_generation_enabled: bool = False
    code_execution_enabled: bool = False

    # Trust scoring profile
    trust_profile: str = "balanced"  # analytical, social, cautious, balanced


class SettingsManager:
    """
    Manage global and per-Qube settings

    Handles loading, saving, and validating settings from YAML and JSON files.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize settings manager

        Args:
            config_dir: Optional custom config directory (defaults to data/config)
        """
        if config_dir is None:
            from utils.paths import get_config_dir
            config_dir = get_config_dir()
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.global_settings_file = self.config_dir / "settings.yaml"
        self.qube_settings_dir = self.config_dir / "qubes"
        self.qube_settings_dir.mkdir(parents=True, exist_ok=True)

        logger.info("settings_manager_initialized", config_dir=str(self.config_dir))

    def load_global_settings(self) -> GlobalSettings:
        """
        Load global settings from YAML

        Returns:
            GlobalSettings instance
        """
        if self.global_settings_file.exists():
            with open(self.global_settings_file, "r") as f:
                data = yaml.safe_load(f) or {}

            logger.debug("global_settings_loaded", file=str(self.global_settings_file))

            return GlobalSettings(**{
                k: v for k, v in data.items()
                if k in GlobalSettings.__annotations__
            })
        else:
            # Create default settings
            settings = GlobalSettings()
            self.save_global_settings(settings)
            logger.info("default_global_settings_created")
            return settings

    def save_global_settings(self, settings: GlobalSettings):
        """
        Save global settings to YAML

        Args:
            settings: GlobalSettings instance to save
        """
        with open(self.global_settings_file, "w") as f:
            yaml.dump(asdict(settings), f, default_flow_style=False, sort_keys=False)

        logger.debug("global_settings_saved", file=str(self.global_settings_file))

    def load_qube_settings(self, qube_id: str) -> QubeSettings:
        """
        Load per-Qube settings

        Args:
            qube_id: Qube ID

        Returns:
            QubeSettings instance
        """
        settings_file = self.qube_settings_dir / f"{qube_id}.yaml"

        if settings_file.exists():
            with open(settings_file, "r") as f:
                data = yaml.safe_load(f) or {}

            logger.debug("qube_settings_loaded", qube_id=qube_id[:16] + "...")

            return QubeSettings(**{
                k: v for k, v in data.items()
                if k in QubeSettings.__annotations__
            })
        else:
            # Create default Qube settings
            settings = QubeSettings()
            self.save_qube_settings(qube_id, settings)
            logger.debug("default_qube_settings_created", qube_id=qube_id[:16] + "...")
            return settings

    def save_qube_settings(self, qube_id: str, settings: QubeSettings):
        """
        Save per-Qube settings

        Args:
            qube_id: Qube ID
            settings: QubeSettings instance to save
        """
        settings_file = self.qube_settings_dir / f"{qube_id}.yaml"

        with open(settings_file, "w") as f:
            yaml.dump(asdict(settings), f, default_flow_style=False, sort_keys=False)

        logger.debug("qube_settings_saved", qube_id=qube_id[:16] + "...")

    def get_effective_settings(
        self,
        qube_id: str,
        global_settings: Optional[GlobalSettings] = None
    ) -> Dict[str, Any]:
        """
        Get effective settings for a Qube (global + overrides)

        Args:
            qube_id: Qube ID
            global_settings: Optional pre-loaded global settings

        Returns:
            Dictionary of effective settings
        """
        if global_settings is None:
            global_settings = self.load_global_settings()

        qube_settings = self.load_qube_settings(qube_id)

        # Start with global settings
        effective = asdict(global_settings)

        # Apply Qube-specific overrides
        qube_dict = asdict(qube_settings)
        for key, value in qube_dict.items():
            if value is not None:  # Only override if explicitly set
                effective[key] = value

        logger.debug("effective_settings_computed", qube_id=qube_id[:16] + "...")

        return effective

    def update_global_setting(self, key: str, value: Any):
        """
        Update a single global setting

        Args:
            key: Setting key
            value: New value
        """
        settings = self.load_global_settings()

        if hasattr(settings, key):
            setattr(settings, key, value)
            self.save_global_settings(settings)
            logger.info("global_setting_updated", key=key, value=value)
        else:
            logger.warning("invalid_global_setting_key", key=key)

    def update_qube_setting(self, qube_id: str, key: str, value: Any):
        """
        Update a single Qube setting

        Args:
            qube_id: Qube ID
            key: Setting key
            value: New value
        """
        settings = self.load_qube_settings(qube_id)

        if hasattr(settings, key):
            setattr(settings, key, value)
            self.save_qube_settings(qube_id, settings)
            logger.info(
                "qube_setting_updated",
                qube_id=qube_id[:16] + "...",
                key=key,
                value=value
            )
        else:
            logger.warning("invalid_qube_setting_key", key=key)

    def reset_global_settings(self):
        """Reset global settings to defaults"""
        settings = GlobalSettings()
        self.save_global_settings(settings)
        logger.info("global_settings_reset")

    def reset_qube_settings(self, qube_id: str):
        """
        Reset Qube settings to defaults

        Args:
            qube_id: Qube ID
        """
        settings = QubeSettings()
        self.save_qube_settings(qube_id, settings)
        logger.info("qube_settings_reset", qube_id=qube_id[:16] + "...")

    def export_settings(self, output_file: Path):
        """
        Export all settings to a single file

        Args:
            output_file: Output file path
        """
        global_settings = self.load_global_settings()

        qube_settings = {}
        for settings_file in self.qube_settings_dir.glob("*.yaml"):
            qube_id = settings_file.stem
            qube_settings[qube_id] = asdict(self.load_qube_settings(qube_id))

        export_data = {
            "global": asdict(global_settings),
            "qubes": qube_settings
        }

        with open(output_file, "w") as f:
            yaml.dump(export_data, f, default_flow_style=False)

        logger.info("settings_exported", file=str(output_file))

    def import_settings(self, import_file: Path):
        """
        Import settings from file

        Args:
            import_file: Import file path
        """
        with open(import_file, "r") as f:
            import_data = yaml.safe_load(f)

        # Import global settings
        if "global" in import_data:
            global_settings = GlobalSettings(**import_data["global"])
            self.save_global_settings(global_settings)

        # Import Qube settings
        if "qubes" in import_data:
            for qube_id, qube_data in import_data["qubes"].items():
                qube_settings = QubeSettings(**qube_data)
                self.save_qube_settings(qube_id, qube_settings)

        logger.info("settings_imported", file=str(import_file))
