"""
Trait Definition System

Defines trait structures and loads configurations from YAML.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml

from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TraitDefinition:
    """Definition of a personality/behavioral trait."""
    name: str
    category: str  # communication, social, emotional, energy, reliability, temperament, intellect, work, dynamics, warning
    description: str
    icon: str
    color: str
    polarity: str  # positive, negative, neutral, warning

    # Detection parameters
    primary_metrics: List[str] = field(default_factory=list)
    supporting_metrics: List[str] = field(default_factory=list)
    negative_indicators: List[str] = field(default_factory=list)
    confidence_threshold: float = 65.0
    evidence_required: int = 4

    # Trait relationships
    opposite_trait: Optional[str] = None
    conflicting_traits: List[str] = field(default_factory=list)
    reinforcing_traits: List[str] = field(default_factory=list)

    # Warning trait flag
    is_warning: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "polarity": self.polarity,
            "primary_metrics": self.primary_metrics,
            "supporting_metrics": self.supporting_metrics,
            "negative_indicators": self.negative_indicators,
            "confidence_threshold": self.confidence_threshold,
            "evidence_required": self.evidence_required,
            "opposite_trait": self.opposite_trait,
            "conflicting_traits": self.conflicting_traits,
            "reinforcing_traits": self.reinforcing_traits,
            "is_warning": self.is_warning,
        }

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'TraitDefinition':
        return cls(
            name=name,
            category=data.get("category", ""),
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            color=data.get("color", "#888888"),
            polarity=data.get("polarity", "neutral"),
            primary_metrics=data.get("primary_metrics", []),
            supporting_metrics=data.get("supporting_metrics", []),
            negative_indicators=data.get("negative_indicators", []),
            confidence_threshold=data.get("confidence_threshold", 65.0),
            evidence_required=data.get("evidence_required", 4),
            opposite_trait=data.get("opposite_trait"),
            conflicting_traits=data.get("conflicting_traits", []),
            reinforcing_traits=data.get("reinforcing_traits", []),
            is_warning=data.get("is_warning", False),
        )


# Warning traits that require special handling
WARNING_TRAITS = [
    "manipulative", "gaslighting", "love-bombing", "ghosting", "breadcrumbing",
    "toxic", "narcissistic", "passive-aggressive", "controlling", "jealous",
    "petty", "two-faced"
]


def load_trait_definitions(config_path: str = "config/trait_definitions.yaml") -> Dict[str, TraitDefinition]:
    """Load trait definitions from YAML config file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning("trait_definitions_not_found", path=str(path))
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        traits = {}
        for name, trait_data in data.get("traits", {}).items():
            traits[name] = TraitDefinition.from_dict(name, trait_data)

        logger.info("trait_definitions_loaded", count=len(traits))
        return traits

    except Exception as e:
        logger.error("trait_definitions_load_failed", error=str(e))
        return {}


def get_trait_definitions_dict(config_path: str = "config/trait_definitions.yaml") -> Dict[str, Dict[str, Any]]:
    """Load trait definitions and return as plain dict (for frontend)."""
    traits = load_trait_definitions(config_path)
    return {name: t.to_dict() for name, t in traits.items()}
