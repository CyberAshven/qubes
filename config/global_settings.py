"""
Global Settings for Qubes Platform

Manages platform-wide configuration including relationship difficulty presets.
These settings apply to ALL qubes, ensuring fairness and consistency.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logging import get_logger

logger = get_logger(__name__)


class GlobalSettings:
    """
    Manages global platform settings

    Includes:
    - Relationship difficulty presets (quick, normal, long, extreme)
    - Trust progression thresholds
    - Minimum interaction requirements
    - Trust growth rate settings
    """

    # Difficulty presets
    PRESETS = {
        "quick": {
            "name": "Quick (~weeks)",
            "description": "Relationships build quickly, suitable for testing or casual use",
            "progression_thresholds": {
                "unmet": 0,
                "stranger": 1,
                "acquaintance": 30,
                "friend": 55,
                "close_friend": 70,
                "best_friend": 85
            },
            "min_interactions": {
                "acquaintance": 3,
                "friend": 5,
                "close_friend": 10,
                "best_friend": 25
            },
            "min_collaborations": {
                "friend": 1,
                "close_friend": 3,
                "best_friend": 10
            }
        },
        "normal": {
            "name": "Normal (~months)",
            "description": "Balanced progression, recommended for most users",
            "progression_thresholds": {
                "unmet": 0,
                "stranger": 1,
                "acquaintance": 45,
                "friend": 65,
                "close_friend": 80,
                "best_friend": 90
            },
            "min_interactions": {
                "acquaintance": 10,
                "friend": 25,
                "close_friend": 75,
                "best_friend": 200
            },
            "min_collaborations": {
                "friend": 2,
                "close_friend": 8,
                "best_friend": 20
            }
        },
        "long": {
            "name": "Long Grind (~years)",
            "description": "Relationships take years to develop, making them truly meaningful",
            "progression_thresholds": {
                "unmet": 0,
                "stranger": 1,
                "acquaintance": 55,
                "friend": 75,
                "close_friend": 88,
                "best_friend": 95
            },
            "min_interactions": {
                "acquaintance": 25,
                "friend": 75,
                "close_friend": 200,
                "best_friend": 500
            },
            "min_collaborations": {
                "friend": 3,
                "close_friend": 15,
                "best_friend": 30
            }
        },
        "extreme": {
            "name": "Extreme (~many years)",
            "description": "MMO-level grind, relationships are extremely rare and precious",
            "progression_thresholds": {
                "unmet": 0,
                "stranger": 1,
                "acquaintance": 60,
                "friend": 80,
                "close_friend": 92,
                "best_friend": 98
            },
            "min_interactions": {
                "acquaintance": 50,
                "friend": 200,
                "close_friend": 500,
                "best_friend": 1000
            },
            "min_collaborations": {
                "friend": 5,
                "close_friend": 25,
                "best_friend": 50
            }
        }
    }

    def __init__(self, settings_file: Optional[Path] = None):
        """
        Initialize global settings

        Args:
            settings_file: Path to settings JSON file (default: config/global_settings.json)
        """
        if settings_file is None:
            settings_file = Path(__file__).parent / "global_settings.json"

        self.settings_file = Path(settings_file)
        self.settings = self._load_settings()

        logger.info(
            "global_settings_loaded",
            difficulty=self.settings.get("relationship_difficulty", "long"),
            settings_file=str(self.settings_file)
        )

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file or create defaults"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                logger.debug("settings_loaded_from_file", file=str(self.settings_file))
                return settings
            except Exception as e:
                logger.error(
                    "failed_to_load_settings",
                    error=str(e),
                    exc_info=True
                )
                return self._get_default_settings()
        else:
            return self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings (long grind mode)"""
        return {
            "relationship_difficulty": "long",
            "custom_thresholds": None,
            "websocket_enabled": True,
            "auto_save": True,
            "version": "1.0"
        }

    def save(self) -> None:
        """Save current settings to file"""
        try:
            # Ensure directory exists
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)

            logger.info("settings_saved", file=str(self.settings_file))
        except Exception as e:
            logger.error(
                "failed_to_save_settings",
                error=str(e),
                exc_info=True
            )

    def get_difficulty(self) -> str:
        """Get current relationship difficulty preset"""
        return self.settings.get("relationship_difficulty", "long")

    def set_difficulty(self, difficulty: str) -> None:
        """
        Set relationship difficulty preset

        Args:
            difficulty: One of "quick", "normal", "long", "extreme"
        """
        if difficulty not in self.PRESETS:
            raise ValueError(f"Invalid difficulty: {difficulty}. Must be one of {list(self.PRESETS.keys())}")

        self.settings["relationship_difficulty"] = difficulty
        self.settings["custom_thresholds"] = None  # Clear custom when using preset
        self.save()

        logger.info("difficulty_changed", new_difficulty=difficulty)

    def get_preset(self, difficulty: Optional[str] = None) -> Dict[str, Any]:
        """
        Get preset configuration for a difficulty level

        Args:
            difficulty: Difficulty level, or None to use current setting

        Returns:
            Preset configuration dict
        """
        if difficulty is None:
            difficulty = self.get_difficulty()

        if difficulty not in self.PRESETS:
            raise ValueError(f"Invalid difficulty: {difficulty}")

        return self.PRESETS[difficulty]

    def get_progression_thresholds(self) -> Dict[str, int]:
        """Get trust score thresholds for relationship progression"""
        if self.settings.get("custom_thresholds"):
            return self.settings["custom_thresholds"]["progression_thresholds"]

        preset = self.get_preset()
        return preset["progression_thresholds"]

    def get_min_interactions(self) -> Dict[str, int]:
        """Get minimum interaction counts for relationship progression"""
        if self.settings.get("custom_thresholds"):
            return self.settings["custom_thresholds"]["min_interactions"]

        preset = self.get_preset()
        return preset["min_interactions"]

    def get_min_collaborations(self) -> Dict[str, int]:
        """Get minimum collaboration counts for relationship progression"""
        if self.settings.get("custom_thresholds"):
            return self.settings["custom_thresholds"].get("min_collaborations", {})

        preset = self.get_preset()
        return preset.get("min_collaborations", {})

    def get_trust_deltas(self) -> Dict[str, Dict[str, float]]:
        """
        DEPRECATED: Trust deltas are now calculated by AI during SUMMARY block creation.
        This method returns an empty dict for backward compatibility.
        """
        return {}

    def set_custom_thresholds(self, thresholds: Dict[str, Any]) -> None:
        """
        Set custom thresholds (overrides presets)

        Args:
            thresholds: Custom configuration matching preset structure
        """
        self.settings["relationship_difficulty"] = "custom"
        self.settings["custom_thresholds"] = thresholds
        self.save()

        logger.info("custom_thresholds_set")

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults"""
        self.settings = self._get_default_settings()
        self.save()

        logger.info("settings_reset_to_defaults")

    def is_websocket_enabled(self) -> bool:
        """Check if WebSocket real-time updates are enabled"""
        return self.settings.get("websocket_enabled", True)

    def set_websocket_enabled(self, enabled: bool) -> None:
        """Enable or disable WebSocket updates"""
        self.settings["websocket_enabled"] = enabled
        self.save()

        logger.info("websocket_settings_changed", enabled=enabled)


# Global singleton instance
_global_settings = None


def get_global_settings() -> GlobalSettings:
    """Get the global settings singleton"""
    global _global_settings
    if _global_settings is None:
        _global_settings = GlobalSettings()
    return _global_settings


def reload_global_settings() -> GlobalSettings:
    """Reload global settings from file"""
    global _global_settings
    _global_settings = GlobalSettings()
    return _global_settings
