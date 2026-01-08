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
class OnboardingPreferences:
    """Track tutorial completion per tab."""

    # Tutorial seen flags for each tab
    qubes_tutorial_seen: bool = False
    dashboard_tutorial_seen: bool = False
    blocks_tutorial_seen: bool = False
    relationships_tutorial_seen: bool = False
    skills_tutorial_seen: bool = False
    economy_tutorial_seen: bool = False
    settings_tutorial_seen: bool = False

    # Master toggle for showing tutorials
    show_tutorials: bool = True


@dataclass
class MemoryConfig:
    """User-configurable memory recall settings."""

    # Basic Settings
    recall_threshold: float = 15.0      # Minimum relevance score (0-100) to recall a memory
    max_recalls: int = 5                # Maximum memories to inject per query
    decay_rate: float = 0.1             # Temporal decay rate (0.1=slow, 1.0=fast)

    # Advanced Settings - Scoring Weights (must sum to ~1.0)
    semantic_weight: float = 0.4        # Weight for semantic/meaning similarity
    keyword_weight: float = 0.3         # Weight for exact keyword matches
    temporal_weight: float = 0.15       # Weight for recency
    relationship_weight: float = 0.1    # Weight for relationship strength with participants


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
    memory: MemoryConfig
    decision: DecisionConfig
    onboarding: OnboardingPreferences

    def __init__(self):
        self.blocks = BlockPreferences()
        self.audio = AudioPreferences()
        self.memory = MemoryConfig()
        self.decision = DecisionConfig()
        self.onboarding = OnboardingPreferences()

    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary."""
        return {
            'blocks': asdict(self.blocks),
            'audio': asdict(self.audio),
            'memory': asdict(self.memory),
            'decision': asdict(self.decision),
            'onboarding': asdict(self.onboarding)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create preferences from dictionary."""
        prefs = cls()

        if 'blocks' in data:
            prefs.blocks = BlockPreferences(**data['blocks'])

        if 'audio' in data:
            prefs.audio = AudioPreferences(**data['audio'])

        if 'memory' in data:
            prefs.memory = MemoryConfig(**data['memory'])

        if 'decision' in data:
            prefs.decision = DecisionConfig(**data['decision'])

        if 'onboarding' in data:
            prefs.onboarding = OnboardingPreferences(**data['onboarding'])

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

    # =========================================================================
    # MEMORY RECALL PREFERENCES
    # =========================================================================

    def update_memory_config(self, **kwargs) -> UserPreferences:
        """
        Update memory recall configuration.

        Args:
            **kwargs: Key-value pairs of MemoryConfig fields to update
                - recall_threshold: Minimum relevance score (0-100)
                - max_recalls: Maximum memories to inject per query
                - decay_rate: Temporal decay rate (0.1=slow, 1.0=fast)
                - semantic_weight: Weight for semantic similarity
                - keyword_weight: Weight for keyword matches
                - temporal_weight: Weight for recency
                - relationship_weight: Weight for relationship strength

        Returns:
            Updated UserPreferences object
        """
        prefs = self.load_preferences()

        for key, value in kwargs.items():
            if hasattr(prefs.memory, key):
                # Validate specific fields
                if key == 'recall_threshold' and not (0 <= value <= 100):
                    raise ValueError("recall_threshold must be between 0 and 100")
                if key == 'max_recalls' and value < 1:
                    raise ValueError("max_recalls must be at least 1")
                if key == 'decay_rate' and not (0 < value <= 1.0):
                    raise ValueError("decay_rate must be between 0 and 1.0")
                if key in ('semantic_weight', 'keyword_weight', 'temporal_weight', 'relationship_weight'):
                    if not (0 <= value <= 1.0):
                        raise ValueError(f"{key} must be between 0 and 1.0")

                setattr(prefs.memory, key, value)

        self.save_preferences(prefs)
        return prefs

    def get_memory_config(self) -> MemoryConfig:
        """Get memory recall configuration."""
        return self.load_preferences().memory

    # =========================================================================
    # DECISION INTELLIGENCE PREFERENCES
    # =========================================================================

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

    # =========================================================================
    # ONBOARDING PREFERENCES
    # =========================================================================

    def get_onboarding_preferences(self) -> OnboardingPreferences:
        """Get onboarding tutorial preferences."""
        return self.load_preferences().onboarding

    def mark_tutorial_seen(self, tab_name: str) -> UserPreferences:
        """
        Mark a specific tab's tutorial as seen.

        Args:
            tab_name: Tab identifier (qubes, dashboard, blocks, etc.)

        Returns:
            Updated UserPreferences object
        """
        prefs = self.load_preferences()
        field_name = f"{tab_name}_tutorial_seen"

        if hasattr(prefs.onboarding, field_name):
            setattr(prefs.onboarding, field_name, True)
            self.save_preferences(prefs)

        return prefs

    def reset_tutorial(self, tab_name: str) -> UserPreferences:
        """
        Reset a specific tab's tutorial to unseen.

        Args:
            tab_name: Tab identifier (qubes, dashboard, blocks, etc.)

        Returns:
            Updated UserPreferences object
        """
        prefs = self.load_preferences()
        field_name = f"{tab_name}_tutorial_seen"

        if hasattr(prefs.onboarding, field_name):
            setattr(prefs.onboarding, field_name, False)
            self.save_preferences(prefs)

        return prefs

    def reset_all_tutorials(self) -> UserPreferences:
        """Reset all tutorials to unseen."""
        prefs = self.load_preferences()
        prefs.onboarding = OnboardingPreferences()  # Reset to defaults (all False)
        self.save_preferences(prefs)
        return prefs

    def update_show_tutorials(self, show: bool) -> UserPreferences:
        """
        Update the master toggle for showing tutorials.

        Args:
            show: Whether to show tutorial prompts

        Returns:
            Updated UserPreferences object
        """
        prefs = self.load_preferences()
        prefs.onboarding.show_tutorials = show
        self.save_preferences(prefs)
        return prefs
