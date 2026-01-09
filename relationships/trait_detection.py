"""
Trait Detection System

Detects and scores traits based on relationship metrics and AI evaluation.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import statistics

from utils.trait_definitions import TraitDefinition, WARNING_TRAITS, load_trait_definitions
from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TraitScore:
    """Tracks confidence and history for a single trait."""
    score: float = 0.0              # 0-100 confidence
    evidence_count: int = 0         # Evaluations supporting this
    first_detected: int = 0         # Unix timestamp
    last_updated: int = 0           # Unix timestamp
    consistency: float = 0.0        # 0-100, score stability
    volatility: float = 0.0         # 0-100, high = inconsistent signals
    trend: str = "stable"           # rising, stable, falling
    source: str = "metric_derived"  # metric_derived, ai_direct, both
    is_confident: bool = False      # Above threshold + sufficient evidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "evidence_count": self.evidence_count,
            "first_detected": self.first_detected,
            "last_updated": self.last_updated,
            "consistency": self.consistency,
            "volatility": self.volatility,
            "trend": self.trend,
            "source": self.source,
            "is_confident": self.is_confident,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TraitScore':
        return cls(
            score=data.get("score", 0.0),
            evidence_count=data.get("evidence_count", 0),
            first_detected=data.get("first_detected", 0),
            last_updated=data.get("last_updated", 0),
            consistency=data.get("consistency", 0.0),
            volatility=data.get("volatility", 0.0),
            trend=data.get("trend", "stable"),
            source=data.get("source", "metric_derived"),
            is_confident=data.get("is_confident", False),
        )


# Difficulty multipliers for evidence requirements
DIFFICULTY_EVIDENCE_MULTIPLIERS = {
    "quick": 0.5,
    "normal": 0.75,
    "long": 1.0,
    "extreme": 2.0,
}

# Difficulty multipliers for confidence growth
DIFFICULTY_GROWTH_RATES = {
    "quick": 1.0,
    "normal": 0.8,
    "long": 0.5,
    "extreme": 0.2,
}

# Decay half-life in days by difficulty
DECAY_HALF_LIFE_DAYS = {
    "quick": 30,
    "normal": 60,
    "long": 90,
    "extreme": 180,
}

# Trust personality boosts for trait categories
PERSONALITY_CATEGORY_BOOSTS = {
    "cautious": {
        "reliability": 1.2,
        "warning": 1.3,
    },
    "social": {
        "communication": 1.2,
        "social": 1.2,
        "emotional": 1.1,
    },
    "analytical": {
        "intellect": 1.2,
        "work": 1.2,
        "reliability": 1.1,
    },
    "balanced": {},
}


class TraitDetector:
    """Detects and scores traits from relationship metrics."""

    def __init__(
        self,
        trait_definitions: Optional[Dict[str, TraitDefinition]] = None,
        difficulty: str = "long",
        trust_personality: str = "balanced",
    ):
        self.definitions = trait_definitions or load_trait_definitions()
        self.difficulty = difficulty
        self.trust_personality = trust_personality

        # Apply difficulty scaling
        self.evidence_multiplier = DIFFICULTY_EVIDENCE_MULTIPLIERS.get(difficulty, 1.0)
        self.growth_rate = DIFFICULTY_GROWTH_RATES.get(difficulty, 0.5)
        self.decay_half_life = DECAY_HALF_LIFE_DAYS.get(difficulty, 90)

        # Get personality boosts
        self.personality_boosts = PERSONALITY_CATEGORY_BOOSTS.get(trust_personality, {})

    def _get_metric_value(self, relationship: Any, metric: str) -> float:
        """Get a metric value from relationship object."""
        value = getattr(relationship, metric, 0.0)
        # Ensure we return a float, handling MagicMock and other non-numeric values
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0

    def _calculate_raw_score(
        self,
        trait_name: str,
        relationship: Any
    ) -> float:
        """Calculate raw trait score from metrics."""
        definition = self.definitions.get(trait_name)
        if not definition:
            return 0.0

        # Primary metrics: 60% weight
        primary_scores = []
        for metric in definition.primary_metrics:
            value = self._get_metric_value(relationship, metric)
            primary_scores.append(value)
        primary_avg = statistics.mean(primary_scores) if primary_scores else 0.0

        # Supporting metrics: 30% weight
        supporting_scores = []
        for metric in definition.supporting_metrics:
            value = self._get_metric_value(relationship, metric)
            supporting_scores.append(value)
        supporting_avg = statistics.mean(supporting_scores) if supporting_scores else 0.0

        # Negative indicators: -10% penalty per high value
        penalty = 0.0
        for metric in definition.negative_indicators:
            value = self._get_metric_value(relationship, metric)
            if value > 30:  # Only penalize if notably present
                penalty += (value / 100) * 10

        # Calculate weighted score
        if primary_scores and supporting_scores:
            raw_score = (primary_avg * 0.6) + (supporting_avg * 0.3) - penalty
        elif primary_scores:
            raw_score = (primary_avg * 0.85) - penalty
        elif supporting_scores:
            raw_score = (supporting_avg * 0.7) - penalty
        elif definition.negative_indicators:
            # Trait detected purely by absence of negative indicators
            # Calculate inverse score from negative indicators
            neg_values = [self._get_metric_value(relationship, m) for m in definition.negative_indicators]
            neg_avg = statistics.mean(neg_values) if neg_values else 0
            raw_score = max(0, 100 - neg_avg * 1.5)  # High negative = low trait score
        else:
            raw_score = 0.0

        # Apply personality boost
        category_boost = self.personality_boosts.get(definition.category, 1.0)
        if definition.is_warning:
            category_boost = self.personality_boosts.get("warning", category_boost)

        return max(0.0, min(100.0, raw_score * category_boost))

    def _get_scaled_evidence_required(self, trait_name: str) -> int:
        """Get evidence required scaled by difficulty."""
        definition = self.definitions.get(trait_name)
        if not definition:
            return 4

        base = definition.evidence_required

        # Warning traits need fewer evaluations
        if definition.is_warning:
            base = 2

        return max(1, int(base * self.evidence_multiplier))

    def _get_confidence_threshold(self, trait_name: str) -> float:
        """Get confidence threshold for trait."""
        definition = self.definitions.get(trait_name)
        if not definition:
            return 65.0

        # Warning traits have higher threshold
        if definition.is_warning:
            return 75.0

        return definition.confidence_threshold

    def _calculate_volatility(
        self,
        trait_name: str,
        relationship: Any,
        new_score: float
    ) -> float:
        """Calculate volatility from recent score history."""
        trait_evolution = getattr(relationship, 'trait_evolution', [])

        # Get recent scores for this trait
        recent_scores = [new_score]
        for entry in reversed(trait_evolution[-10:]):  # Last 10 entries
            if entry.get("trait") == trait_name:
                recent_scores.append(entry.get("new_score", 0))
                if len(recent_scores) >= 5:
                    break

        if len(recent_scores) < 2:
            return 0.0

        # Calculate standard deviation
        try:
            stdev = statistics.stdev(recent_scores)
            # Normalize to 0-100 scale (25+ stdev = high volatility)
            return min(100.0, stdev * 4)
        except Exception:
            return 0.0

    def _determine_trend(
        self,
        old_score: Optional[TraitScore],
        new_score: float
    ) -> str:
        """Determine if trait is rising, stable, or falling."""
        if not old_score:
            return "stable"

        diff = new_score - old_score.score
        if diff > 5:
            return "rising"
        elif diff < -5:
            return "falling"
        return "stable"

    def _apply_decay(
        self,
        trait_score: TraitScore,
        days_since_update: int
    ) -> float:
        """Apply time-based decay to trait score."""
        if days_since_update <= 0:
            return trait_score.score

        # Calculate decay factor using half-life formula
        # score * (0.5 ^ (days / half_life))
        decay_factor = 0.5 ** (days_since_update / self.decay_half_life)
        return trait_score.score * decay_factor

    def detect_traits(
        self,
        relationship: Any,
        evaluation: Dict[str, Any],
        ai_detected: Optional[List[str]] = None,
        ai_evidence: Optional[Dict[str, str]] = None,
    ) -> Dict[str, TraitScore]:
        """
        Detect all traits based on metrics and AI evaluation.

        Args:
            relationship: Relationship object with metrics
            evaluation: AI evaluation with deltas
            ai_detected: List of traits AI directly identified
            ai_evidence: Dict of trait -> evidence string

        Returns:
            Dict of trait_name -> TraitScore
        """
        ai_detected = ai_detected or []
        ai_evidence = ai_evidence or {}

        now = int(datetime.now(timezone.utc).timestamp())
        existing_traits = getattr(relationship, 'trait_scores', {})
        new_traits: Dict[str, TraitScore] = {}

        for trait_name, definition in self.definitions.items():
            # Calculate metric-derived score
            metric_score = self._calculate_raw_score(trait_name, relationship)

            # Check if AI also detected this trait
            ai_boost = 1.2 if trait_name in ai_detected else 1.0
            ai_only = trait_name in ai_detected and metric_score < 30

            # Calculate final score
            if ai_only:
                # AI-only detection starts lower
                final_score = 50.0
                source = "ai_direct"
            elif trait_name in ai_detected:
                # Both AI and metrics agree
                final_score = min(100.0, metric_score * ai_boost)
                source = "both"
            else:
                final_score = metric_score
                source = "metric_derived"

            # Apply growth rate scaling for changes
            old_trait = existing_traits.get(trait_name)
            if old_trait:
                old_score_value = old_trait.score if isinstance(old_trait, TraitScore) else old_trait.get("score", 0)

                # Apply decay before calculating delta
                if isinstance(old_trait, dict):
                    last_updated = old_trait.get("last_updated", now)
                else:
                    last_updated = old_trait.last_updated
                days_since = (now - last_updated) / 86400
                if days_since > 1:
                    decayed_score = self._apply_decay(
                        TraitScore.from_dict(old_trait) if isinstance(old_trait, dict) else old_trait,
                        int(days_since)
                    )
                    old_score_value = decayed_score

                delta = final_score - old_score_value
                scaled_delta = delta * self.growth_rate
                final_score = old_score_value + scaled_delta

            # Only track traits above minimum threshold (25% = emerging)
            if final_score < 25 and trait_name not in existing_traits:
                continue

            # Get or create trait score
            if trait_name in existing_traits:
                old_data = existing_traits[trait_name]
                if isinstance(old_data, dict):
                    old_trait = TraitScore.from_dict(old_data)
                else:
                    old_trait = old_data
                evidence_count = old_trait.evidence_count + 1
                first_detected = old_trait.first_detected
            else:
                old_trait = None
                evidence_count = 1
                first_detected = now

            # Calculate volatility
            volatility = self._calculate_volatility(trait_name, relationship, final_score)

            # Determine if confident
            threshold = self._get_confidence_threshold(trait_name)
            evidence_required = self._get_scaled_evidence_required(trait_name)
            is_confident = final_score >= threshold and evidence_count >= evidence_required

            # Create trait score
            new_traits[trait_name] = TraitScore(
                score=round(final_score, 1),
                evidence_count=evidence_count,
                first_detected=first_detected,
                last_updated=now,
                consistency=100.0 - volatility,
                volatility=round(volatility, 1),
                trend=self._determine_trend(old_trait, final_score),
                source=source,
                is_confident=is_confident,
            )

        return new_traits

    def get_confident_traits(
        self,
        trait_scores: Dict[str, TraitScore]
    ) -> List[str]:
        """Get list of trait names that are confident."""
        return [
            name for name, score in trait_scores.items()
            if score.is_confident
        ]

    def get_emerging_traits(
        self,
        trait_scores: Dict[str, TraitScore],
        min_score: float = 40.0
    ) -> List[str]:
        """Get list of traits that are emerging (not confident yet)."""
        return [
            name for name, score in trait_scores.items()
            if not score.is_confident and score.score >= min_score
        ]

    def get_warning_traits(
        self,
        trait_scores: Dict[str, TraitScore]
    ) -> List[str]:
        """Get list of warning traits (confident or emerging)."""
        warning = []
        for name, score in trait_scores.items():
            if name in WARNING_TRAITS:
                # Show warning traits even below threshold if score > 40
                if score.is_confident or score.score >= 40:
                    warning.append(name)
        return warning

    def get_trait_changes(
        self,
        old_traits: Dict[str, Any],
        new_traits: Dict[str, TraitScore],
        threshold: float = 3.0
    ) -> Dict[str, List[str]]:
        """
        Calculate trait changes between old and new states.

        Returns:
            Dict with keys: assigned, strengthened, weakened, removed
        """
        changes = {
            "assigned": [],
            "strengthened": [],
            "weakened": [],
            "removed": [],
        }

        # Check for new and changed traits
        for trait_name, new_score in new_traits.items():
            if trait_name not in old_traits:
                changes["assigned"].append(trait_name)
            else:
                old_data = old_traits[trait_name]
                old_score_value = old_data.get("score", 0) if isinstance(old_data, dict) else old_data.score

                if new_score.score > old_score_value + threshold:
                    changes["strengthened"].append(trait_name)
                elif new_score.score < old_score_value - threshold:
                    changes["weakened"].append(trait_name)

        # Check for removed traits (below minimum threshold)
        for trait_name in old_traits:
            if trait_name not in new_traits:
                changes["removed"].append(trait_name)

        return changes
