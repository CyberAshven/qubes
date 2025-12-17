"""
Trust Scoring System

Implements configurable trust score calculation and component updates.
From docs/15_Key_Algorithms.md Section 11.1
"""

import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from relationships.relationship import Relationship
from utils.logging import get_logger

logger = get_logger(__name__)


def _get_global_settings():
    """Lazy import to avoid circular dependency"""
    try:
        from config.global_settings import get_global_settings
        return get_global_settings()
    except ImportError:
        return None


class TrustScorer:
    """
    Configurable trust scoring system

    Calculates overall trust scores using weighted components and applies
    penalties for negative behaviors. Configuration loaded from YAML.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize trust scorer

        Args:
            config_path: Path to trust_scoring.yaml (default: config/trust_scoring.yaml)
        """
        if config_path is None:
            config_path = Path("config/trust_scoring.yaml")

        self.config_path = Path(config_path)
        self.config = self._load_config()

        logger.info(
            "trust_scorer_initialized",
            config_path=str(self.config_path)
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load trust scoring configuration from YAML"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Validate default weights
            weights = config.get("default_weights", {})
            total = sum(weights.values())
            if not (0.99 <= total <= 1.01):
                raise ValueError(f"Default weights must sum to 1.0, got {total}")

            # Validate profile weights
            for profile_name, profile_weights in config.get("qube_profiles", {}).items():
                total = sum(profile_weights.values())
                if not (0.99 <= total <= 1.01):
                    raise ValueError(
                        f"Profile '{profile_name}' weights must sum to 1.0, got {total}"
                    )

            logger.debug("trust_config_loaded", profiles=len(config.get("qube_profiles", {})))
            return config

        except FileNotFoundError:
            logger.warning(
                "trust_config_not_found",
                path=str(self.config_path),
                message="Using default configuration"
            )
            return self._get_default_config()

        except Exception as e:
            logger.error(
                "trust_config_load_failed",
                error=str(e),
                exc_info=True
            )
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if file not found"""
        return {
            "default_weights": {
                "reliability": 0.25,
                "honesty": 0.30,
                "responsiveness": 0.15,
                "expertise": 0.15,
                "third_party_reputation": 0.15
            },
            "default_penalties": {
                "warning_multiplier": 5,
                "dispute_multiplier": 3
            },
            "progression_thresholds": {
                "unmet": 0,
                "stranger": 1,
                "acquaintance": 55,      # Was 40 - LONG GRIND MODE
                "friend": 75,            # Was 65 - LONG GRIND MODE
                "close_friend": 88,      # Was 80 - LONG GRIND MODE
                "best_friend": 95        # Was 90 - LONG GRIND MODE
            },
            "min_interactions": {
                "acquaintance": 25,      # Was 5 - LONG GRIND MODE (5x harder)
                "friend": 75,            # Was 10 - LONG GRIND MODE (7.5x harder)
                "close_friend": 200,     # Was 20 - LONG GRIND MODE (10x harder)
                "best_friend": 500       # Was 50 - LONG GRIND MODE (10x harder)
            }
        }

    def calculate_trust_score(
        self,
        relationship: Relationship,
        profile: Optional[str] = None
    ) -> float:
        """
        Calculate overall trust score for a relationship

        From docs/15_Key_Algorithms.md Section 11.1

        Args:
            relationship: Relationship instance
            profile: Trust profile name (e.g., "analytical", "social", "cautious")
                    If None, uses default weights

        Returns:
            Trust score 0-100
        """
        # Get weights from profile or use defaults
        if profile and profile in self.config.get("qube_profiles", {}):
            weights = self.config["qube_profiles"][profile]
            logger.debug("using_trust_profile", profile=profile)
        else:
            weights = self.config["default_weights"]

        # NOTE: Trust is now calculated using Relationship.calculate_trust_score()
        # This method uses the new formula: reliability*0.3 + honesty*0.3 +
        # responsiveness*0.15 + expertise*0.15 + loyalty*0.10

        # For backward compatibility, we use the relationship's built-in calculation
        overall = relationship.calculate_trust_score()

        # Clamp to 0-100
        final_score = max(0, min(100, overall))

        logger.debug(
            "trust_score_calculated",
            entity_id=relationship.entity_id,
            base_score=round(overall, 2),
            final_score=round(final_score, 2),
            profile=profile or "default"
        )

        return round(final_score, 2)

    def update_trust_component(
        self,
        relationship: Relationship,
        component: str,
        delta: float,
        reason: Optional[str] = None
    ) -> None:
        """
        Update a specific trust component

        Args:
            relationship: Relationship to update
            component: Component name ("reliability", "honesty", "responsiveness")
            delta: Change amount (-100 to +100)
            reason: Optional reason for the change
        """
        if component == "reliability":
            old_score = relationship.reliability
            relationship.reliability = max(0, min(100, old_score + delta))
            new_score = relationship.reliability

        elif component == "honesty":
            old_score = relationship.honesty
            relationship.honesty = max(0, min(100, old_score + delta))
            new_score = relationship.honesty

        elif component == "responsiveness":
            old_score = relationship.responsiveness
            relationship.responsiveness = max(0, min(100, old_score + delta))
            new_score = relationship.responsiveness

        else:
            logger.warning(
                "unknown_trust_component",
                component=component,
                entity_id=relationship.entity_id
            )
            return

        logger.info(
            "trust_component_updated",
            entity_id=relationship.entity_id,
            component=component,
            old_score=old_score,
            new_score=new_score,
            delta=delta,
            reason=reason
        )

    def update_reliability(
        self,
        relationship: Relationship,
        task_succeeded: bool,
        importance: float = 1.0
    ) -> None:
        """
        Update reliability score based on task outcome

        Args:
            relationship: Relationship to update
            task_succeeded: Whether task was completed successfully
            importance: Importance multiplier (0.1 to 3.0)
        """
        # Get trust deltas from global settings
        global_settings = _get_global_settings()
        if global_settings:
            trust_deltas = global_settings.get_trust_deltas()
            reliability_deltas = trust_deltas.get("reliability", {})
            success_delta = reliability_deltas.get("success", 0.4)
            failure_delta = reliability_deltas.get("failure", -1.0)
        else:
            # Fallback to hardcoded (long grind mode)
            success_delta = 0.4  # Was 2.0 - Successful tasks increase reliability slowly
            failure_delta = -1.0  # Was -5.0 - Failed tasks hurt less (less punishing)

        if task_succeeded:
            delta = success_delta * importance
        else:
            delta = failure_delta * importance

        self.update_trust_component(
            relationship,
            "reliability",
            delta,
            reason=f"Task {'succeeded' if task_succeeded else 'failed'}"
        )

    def update_responsiveness(
        self,
        relationship: Relationship,
        response_time_seconds: float,
        expected_time_seconds: float = 300
    ) -> None:
        """
        Update responsiveness score based on response time

        Args:
            relationship: Relationship to update
            response_time_seconds: Actual response time
            expected_time_seconds: Expected response time (default: 5 minutes)
        """
        # Update running average
        if relationship.messages_received > 0:
            old_avg = relationship.response_time_avg
            new_avg = (
                (old_avg * (relationship.messages_received - 1) + response_time_seconds)
                / relationship.messages_received
            )
            relationship.response_time_avg = new_avg
        else:
            relationship.response_time_avg = response_time_seconds

        # Calculate delta based on how response compares to expected
        ratio = response_time_seconds / expected_time_seconds

        # Get trust deltas from global settings
        global_settings = _get_global_settings()
        if global_settings:
            trust_deltas = global_settings.get_trust_deltas()
            responsiveness_deltas = trust_deltas.get("responsiveness", {})
            very_fast = responsiveness_deltas.get("very_fast", 3.0)
            fast = responsiveness_deltas.get("fast", 1.0)
            slow = responsiveness_deltas.get("slow", -0.5)
            very_slow = responsiveness_deltas.get("very_slow", -2.0)
        else:
            # Fallback to hardcoded (default mode - faster than long grind)
            very_fast = 3.0
            fast = 1.0
            slow = -0.5
            very_slow = -2.0

        if ratio < 0.5:
            delta = very_fast  # Very fast response
        elif ratio < 1.0:
            delta = fast  # Good response time
        elif ratio < 2.0:
            delta = slow  # Slightly slow
        else:
            delta = very_slow  # Very slow response

        self.update_trust_component(
            relationship,
            "responsiveness",
            delta,
            reason=f"Response time: {response_time_seconds:.1f}s"
        )

    def apply_penalty(
        self,
        relationship: Relationship,
        penalty_type: str,
        reason: str
    ) -> None:
        """
        DEPRECATED: Penalty system removed in favor of AI-driven evaluation.
        This method is kept for backward compatibility but does nothing.

        Args:
            relationship: Relationship to penalize
            penalty_type: "warning" or "dispute"
            reason: Reason for penalty
        """
        logger.warning(
            "deprecated_penalty_system_called",
            entity_id=relationship.entity_id,
            penalty_type=penalty_type,
            reason=reason,
            message="Penalty system deprecated - trust is now AI-driven"
        )

    def calculate_compatibility(self, relationship: Relationship) -> float:
        """
        DEPRECATED: Compatibility is now AI-evaluated, not calculated.
        This method is kept for backward compatibility.

        Args:
            relationship: Relationship to score

        Returns:
            Compatibility score from AI evaluation (0-100)
        """
        logger.debug(
            "deprecated_compatibility_calculation",
            entity_id=relationship.entity_id,
            message="Compatibility is now AI-evaluated"
        )
        return relationship.compatibility

    def get_progression_threshold(self, status: str) -> int:
        """Get minimum trust score required for a relationship status"""
        # Check global settings first
        global_settings = _get_global_settings()
        if global_settings:
            thresholds = global_settings.get_progression_thresholds()
            return thresholds.get(status, 0)

        # Fall back to config
        thresholds = self.config.get("progression_thresholds", {})
        return thresholds.get(status, 0)

    def get_min_interactions(self, status: str) -> int:
        """Get minimum interaction count required for a relationship status"""
        # Check global settings first
        global_settings = _get_global_settings()
        if global_settings:
            min_interactions = global_settings.get_min_interactions()
            return min_interactions.get(status, 0)

        # Fall back to config
        min_interactions = self.config.get("min_interactions", {})
        return min_interactions.get(status, 0)
