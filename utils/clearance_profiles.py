"""
Clearance Profile System

Defines customizable clearance tiers and their default configurations.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

from utils.logging import get_logger

logger = get_logger(__name__)


# Clearance hierarchy values
CLEARANCE_HIERARCHY = {
    "none": 0,
    "public": 1,
    "professional": 2,
    "social": 3,
    "trusted": 4,
    "inner_circle": 5,
    "family": 6,
}

LEVEL_TO_NAME = {v: k for k, v in CLEARANCE_HIERARCHY.items()}


@dataclass
class ClearanceProfile:
    """Definition of a clearance tier."""
    name: str
    level: int
    description: str
    categories: List[str]  # Owner info categories included
    fields: List[str]  # Specific fields, or ["*"] for all in categories
    excluded_fields: List[str]  # Fields to block even if category matches
    icon: str
    color: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "description": self.description,
            "categories": self.categories,
            "fields": self.fields,
            "excluded_fields": self.excluded_fields,
            "icon": self.icon,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClearanceProfile':
        return cls(**data)


# Default profiles - can be customized per Qube
# Display names: None, Minimal, Limited, Standard, Extended, Full, Complete
DEFAULT_PROFILES: Dict[str, ClearanceProfile] = {
    "none": ClearanceProfile(
        name="none",
        level=0,
        description="No access to owner information",
        categories=[],
        fields=[],
        excluded_fields=["*"],
        icon="🚫",
        color="#666666"
    ),
    "public": ClearanceProfile(
        name="public",
        level=1,
        description="Name and occupation only",
        categories=["standard"],
        fields=["name", "nickname", "occupation"],
        excluded_fields=[],
        icon="🌐",
        color="#888888"
    ),
    "professional": ClearanceProfile(
        name="professional",
        level=2,
        description="Work-related information",
        categories=["standard"],
        fields=["name", "nickname", "occupation", "employer", "job_title"],
        excluded_fields=["home_address", "personal_phone"],
        icon="💼",
        color="#4a90e2"
    ),
    "social": ClearanceProfile(
        name="social",
        level=3,
        description="General personal information",
        categories=["standard", "preferences"],
        fields=["*"],
        excluded_fields=["address", "phone", "ssn", "medical"],
        icon="🎉",
        color="#ffaa00"
    ),
    "trusted": ClearanceProfile(
        name="trusted",
        level=4,
        description="Contact info and preferences",
        categories=["standard", "preferences", "dates"],
        fields=["*"],
        excluded_fields=["ssn", "passwords", "medical"],
        icon="🔒",
        color="#00cc66"
    ),
    "inner_circle": ClearanceProfile(
        name="inner_circle",
        level=5,
        description="Nearly all personal information",
        categories=["standard", "preferences", "dates", "people", "physical"],
        fields=["*"],
        excluded_fields=["ssn", "passwords"],
        icon="💫",
        color="#00ff88"
    ),
    "family": ClearanceProfile(
        name="family",
        level=6,
        description="All information including medical",
        categories=["standard", "preferences", "dates", "people", "physical", "medical"],
        fields=["*"],
        excluded_fields=["ssn", "passwords"],
        icon="👨‍👩‍👧‍👦",
        color="#ff69b4"
    ),
}


@dataclass
class TagDefinition:
    """Definition of a relationship tag (organizational only, no clearance effects)."""
    name: str
    description: str
    icon: str
    color: str
    is_default: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "is_default": self.is_default,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TagDefinition':
        # Handle legacy data that might still have clearance_modifier
        data.pop("clearance_modifier", None)
        return cls(**data)


DEFAULT_TAGS: Dict[str, TagDefinition] = {
    "family": TagDefinition("family", "Blood/legal relatives", "👨‍👩‍👧‍👦", "#ff69b4"),
    "romantic": TagDefinition("romantic", "Partner, spouse, dating", "💕", "#ff1493"),
    "coworker": TagDefinition("coworker", "Professional colleagues", "💼", "#4a90e2"),
    "classmate": TagDefinition("classmate", "School/education context", "🎓", "#9b59b6"),
    "neighbor": TagDefinition("neighbor", "Physical proximity", "🏠", "#27ae60"),
    "mentor": TagDefinition("mentor", "Teacher, advisor", "🧑‍🏫", "#f39c12"),
    "mentee": TagDefinition("mentee", "Someone you guide", "📚", "#3498db"),
    "online": TagDefinition("online", "Internet-only relationship", "🌐", "#95a5a6"),
    "ex": TagDefinition("ex", "Former romantic partner", "💔", "#e74c3c"),
    "estranged": TagDefinition("estranged", "Distanced relationship", "🚪", "#7f8c8d"),
}


class ClearanceConfig:
    """Per-Qube clearance configuration."""

    def __init__(self, qube_dir: Path):
        self.qube_dir = Path(qube_dir)
        self.config_dir = self.qube_dir / "clearance"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"

        self.profiles: Dict[str, ClearanceProfile] = {}
        self.custom_tags: Dict[str, TagDefinition] = {}
        self.auto_suggest_enabled: bool = True

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from disk."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)

                # Load custom profiles (merged with defaults)
                for name, profile_data in data.get("profiles", {}).items():
                    self.profiles[name] = ClearanceProfile.from_dict(profile_data)

                # Load custom tags
                for name, tag_data in data.get("custom_tags", {}).items():
                    tag_data["is_default"] = False
                    self.custom_tags[name] = TagDefinition.from_dict(tag_data)

                self.auto_suggest_enabled = data.get("auto_suggest_enabled", True)

            except Exception as e:
                logger.error("clearance_config_load_failed", error=str(e))

    def _save_config(self) -> None:
        """Save configuration to disk."""
        try:
            data = {
                "profiles": {name: p.to_dict() for name, p in self.profiles.items()},
                "custom_tags": {name: t.to_dict() for name, t in self.custom_tags.items()},
                "auto_suggest_enabled": self.auto_suggest_enabled,
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("clearance_config_save_failed", error=str(e))

    def get_profile(self, name: str) -> ClearanceProfile:
        """Get profile by name, falling back to defaults."""
        if name in self.profiles:
            return self.profiles[name]
        return DEFAULT_PROFILES.get(name, DEFAULT_PROFILES["none"])

    def get_all_profiles(self) -> Dict[str, ClearanceProfile]:
        """Get all profiles (custom overrides + defaults)."""
        result = dict(DEFAULT_PROFILES)
        result.update(self.profiles)
        return result

    def update_profile(self, name: str, updates: Dict[str, Any]) -> ClearanceProfile:
        """Update a profile's configuration."""
        base = self.get_profile(name)
        updated_data = base.to_dict()
        updated_data.update(updates)
        self.profiles[name] = ClearanceProfile.from_dict(updated_data)
        self._save_config()
        return self.profiles[name]

    def get_tag(self, name: str) -> Optional[TagDefinition]:
        """Get tag definition by name."""
        if name in self.custom_tags:
            return self.custom_tags[name]
        return DEFAULT_TAGS.get(name)

    def get_all_tags(self) -> Dict[str, TagDefinition]:
        """Get all tags (custom + defaults)."""
        result = dict(DEFAULT_TAGS)
        result.update(self.custom_tags)
        return result

    def create_custom_tag(self, name: str, description: str,
                          icon: str, color: str) -> TagDefinition:
        """Create a new custom tag."""
        tag = TagDefinition(name, description, icon, color, is_default=False)
        self.custom_tags[name] = tag
        self._save_config()
        return tag

    def delete_custom_tag(self, name: str) -> bool:
        """Delete a custom tag (cannot delete defaults)."""
        if name in self.custom_tags:
            del self.custom_tags[name]
            self._save_config()
            return True
        return False
