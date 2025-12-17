"""
User Preferences Management

Manages non-sensitive user preferences like auto-anchor settings,
UI preferences, and other configuration options.

Unlike API keys, these preferences don't require encryption and are
stored in plain JSON for easy access and modification.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class BlockPreferences:
    """Preferences for blockchain anchoring behavior."""

    # Individual chat settings
    individual_auto_anchor: bool = True
    individual_anchor_threshold: int = 10  # Anchor every N blocks

    # Group chat settings
    group_auto_anchor: bool = True
    group_anchor_threshold: int = 5  # Anchor more frequently in group chats


@dataclass
class AudioPreferences:
    """Preferences for audio/TTS configuration."""

    # Google Cloud TTS credentials path (optional)
    google_tts_credentials_path: Optional[str] = None


@dataclass
class DecisionConfig:
    """User-configurable decision intelligence settings."""

    # Trust & Relationship Thresholds (0-100)
    trust_threshold: int = 70
    expertise_threshold: int = 60
    collaboration_threshold: int = 65

    # Self-Evaluation Thresholds (0-100)
    confidence_threshold: int = 60
    humility_threshold: int = 70

    # Influence Levels (0-100%)
    metric_influence: int = 70
    validation_strictness: int = 50  # 0=Soft, 50=Medium, 100=Hard

    # Negative Metric Tolerances (0-100)
    max_antagonism: int = 30
    max_distrust: int = 40
    max_betrayal: int = 10

    # Feature Toggles
    enable_auto_temperature: bool = True
    enable_validation_layer: bool = True
    enable_metric_tools: bool = True
    auto_thresholds: bool = False  # Auto-derive thresholds from self-evaluation


@dataclass
class UserPreferences:
    """Complete user preferences."""

    blocks: BlockPreferences
    audio: AudioPreferences
    decision: DecisionConfig

    def __init__(self):
        self.blocks = BlockPreferences()
        self.audio = AudioPreferences()
        self.decision = DecisionConfig()

    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary."""
        return {
            'blocks': asdict(self.blocks),
            'audio': asdict(self.audio),
            'decision': asdict(self.decision)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create preferences from dictionary."""
        prefs = cls()

        if 'blocks' in data:
            prefs.blocks = BlockPreferences(**data['blocks'])

        if 'audio' in data:
            prefs.audio = AudioPreferences(**data['audio'])

        if 'decision' in data:
            prefs.decision = DecisionConfig(**data['decision'])

        return prefs


class UserPreferencesManager:
    """Manages user preferences storage and retrieval."""

    def __init__(self, user_data_dir: Path):
        """
        Initialize preferences manager.

        Args:
            user_data_dir: Directory for user data (e.g., data/users/{user_id}/)
        """
        self.user_data_dir = Path(user_data_dir)
        self.prefs_file = self.user_data_dir / "preferences.json"

        # Ensure directory exists
        self.user_data_dir.mkdir(parents=True, exist_ok=True)

    def load_preferences(self) -> UserPreferences:
        """
        Load user preferences from file.

        Returns:
            UserPreferences object (default if file doesn't exist)
        """
        if not self.prefs_file.exists():
            return UserPreferences()

        try:
            with open(self.prefs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return UserPreferences.from_dict(data)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading preferences: {e}")
            # Return defaults on error
            return UserPreferences()

    def save_preferences(self, preferences: UserPreferences) -> None:
        """
        Save user preferences to file.

        Args:
            preferences: UserPreferences object to save
        """
        with open(self.prefs_file, 'w', encoding='utf-8') as f:
            json.dump(preferences.to_dict(), f, indent=2)

    def update_block_preferences(
        self,
        individual_auto_anchor: Optional[bool] = None,
        individual_anchor_threshold: Optional[int] = None,
        group_auto_anchor: Optional[bool] = None,
        group_anchor_threshold: Optional[int] = None
    ) -> UserPreferences:
        """
        Update block-related preferences.

        Args:
            individual_auto_anchor: Enable/disable auto-anchor for individual chats
            individual_anchor_threshold: Blocks between anchors for individual chats
            group_auto_anchor: Enable/disable auto-anchor for group chats
            group_anchor_threshold: Blocks between anchors for group chats

        Returns:
            Updated UserPreferences object
        """
        prefs = self.load_preferences()

        if individual_auto_anchor is not None:
            prefs.blocks.individual_auto_anchor = individual_auto_anchor

        if individual_anchor_threshold is not None:
            if individual_anchor_threshold < 1:
                raise ValueError("Anchor threshold must be at least 1")
            prefs.blocks.individual_anchor_threshold = individual_anchor_threshold

        if group_auto_anchor is not None:
            prefs.blocks.group_auto_anchor = group_auto_anchor

        if group_anchor_threshold is not None:
            if group_anchor_threshold < 1:
                raise ValueError("Anchor threshold must be at least 1")
            prefs.blocks.group_anchor_threshold = group_anchor_threshold

        self.save_preferences(prefs)
        return prefs

    def get_block_preferences(self) -> BlockPreferences:
        """Get block-related preferences."""
        return self.load_preferences().blocks

    def update_google_tts_path(self, path: Optional[str]) -> UserPreferences:
        """
        Update Google Cloud TTS credentials path.

        Args:
            path: Path to Google Cloud service account JSON file (or None to clear)

        Returns:
            Updated UserPreferences object
        """
        prefs = self.load_preferences()
        prefs.audio.google_tts_credentials_path = path
        self.save_preferences(prefs)
        return prefs

    def get_google_tts_path(self) -> Optional[str]:
        """Get Google Cloud TTS credentials path."""
        return self.load_preferences().audio.google_tts_credentials_path

    def get_audio_preferences(self) -> AudioPreferences:
        """Get audio-related preferences."""
        return self.load_preferences().audio

    def update_decision_config(self, **kwargs) -> UserPreferences:
        """
        Update decision intelligence configuration.

        Args:
            **kwargs: Key-value pairs of DecisionConfig fields to update

        Returns:
            Updated UserPreferences object
        """
        prefs = self.load_preferences()

        for key, value in kwargs.items():
            if hasattr(prefs.decision, key):
                setattr(prefs.decision, key, value)

        self.save_preferences(prefs)
        return prefs

    def get_decision_config(self) -> DecisionConfig:
        """Get decision intelligence configuration."""
        return self.load_preferences().decision

    def reset_to_defaults(self) -> UserPreferences:
        """Reset all preferences to defaults."""
        prefs = UserPreferences()
        self.save_preferences(prefs)
        return prefs
