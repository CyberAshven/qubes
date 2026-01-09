# Trait System Implementation Blueprint

## Overview

This blueprint provides exact file paths, line numbers, and code changes needed to implement the Trait System. It maps directly to the existing codebase structure.

---

## PART 1: BACKEND CHANGES

### 1.1 New File: `utils/trait_definitions.py`

**Purpose**: Define TraitDefinition class and load trait configurations

```python
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
```

---

### 1.2 New File: `relationships/trait_detection.py`

**Purpose**: TraitDetector class for detecting traits from metrics

```python
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

        # Get personality boosts
        self.personality_boosts = PERSONALITY_CATEGORY_BOOSTS.get(trust_personality, {})

    def _get_metric_value(self, relationship: Any, metric: str) -> float:
        """Get a metric value from relationship object."""
        return getattr(relationship, metric, 0.0)

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
        raw_score = (primary_avg * 0.6) + (supporting_avg * 0.3) - penalty

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
        except:
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
```

---

### 1.3 Modify: `relationships/relationship.py`

#### Line ~65: Add TraitScore import and dataclass

**BEFORE** the `class Relationship:` definition (around line 65), add:

```python
from dataclasses import dataclass

@dataclass
class TraitScore:
    """Tracks confidence and history for a single trait."""
    score: float = 0.0
    evidence_count: int = 0
    first_detected: int = 0
    last_updated: int = 0
    consistency: float = 0.0
    volatility: float = 0.0
    trend: str = "stable"
    source: str = "metric_derived"
    is_confident: bool = False

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
        return cls(**{k: data.get(k, getattr(cls, k, None)) for k in cls.__dataclass_fields__})
```

#### Line 181: Add trait fields after `tags`

**AFTER** `self.tags: List[str] = []` (line 181), add:

```python
        # Traits - AI-attributed personality/behavioral characteristics
        self.trait_scores: Dict[str, Any] = {}  # trait_name -> TraitScore dict
        self.trait_evolution: List[Dict[str, Any]] = []  # Timeline of changes
        self.manual_trait_overrides: Dict[str, bool] = {}  # User overrides
        self.trait_scores_version: str = "1.0"  # For migration
```

#### Line ~485: Update `to_dict()` method

**AFTER** the tags serialization (around line 485), add:

```python
            # Traits
            "trait_scores": {
                name: (ts.to_dict() if hasattr(ts, 'to_dict') else ts)
                for name, ts in self.trait_scores.items()
            },
            "trait_evolution": self.trait_evolution,
            "manual_trait_overrides": self.manual_trait_overrides,
            "trait_scores_version": self.trait_scores_version,
```

#### Line ~578: Update `from_dict()` method

**AFTER** the tags loading (around line 578), add:

```python
        # Traits
        rel.trait_scores = data.get("trait_scores", {})
        rel.trait_evolution = data.get("trait_evolution", [])
        rel.manual_trait_overrides = data.get("manual_trait_overrides", {})
        rel.trait_scores_version = data.get("trait_scores_version", "1.0")
```

---

### 1.4 Modify: `core/session.py`

#### Line ~1173: Add TraitDetector import

At the top of the file with other imports:

```python
from relationships.trait_detection import TraitDetector
from utils.trait_definitions import load_trait_definitions
```

#### Line ~1419: Add trait detection after evaluation storage

**AFTER** the evaluation is appended to `rel.evaluations` (around line 1418), add:

```python
            # Detect and update traits
            try:
                trait_definitions = load_trait_definitions()
                trait_detector = TraitDetector(
                    trait_definitions=trait_definitions,
                    difficulty=getattr(self, 'relationship_difficulty', 'long'),
                    trust_personality=getattr(self.qube, 'trust_personality', 'balanced'),
                )

                # Get AI-detected traits from evaluation if present
                ai_detected = evaluation.get("detected_traits", [])
                ai_evidence = evaluation.get("trait_evidence", {})

                # Detect traits
                old_trait_scores = dict(rel.trait_scores)
                new_trait_scores = trait_detector.detect_traits(
                    rel,
                    evaluation,
                    ai_detected=ai_detected,
                    ai_evidence=ai_evidence,
                )

                # Update relationship trait scores
                rel.trait_scores = {
                    name: score.to_dict() if hasattr(score, 'to_dict') else score
                    for name, score in new_trait_scores.items()
                }

                # Log significant trait changes to evolution
                for trait_name, new_score in new_trait_scores.items():
                    old_score_data = old_trait_scores.get(trait_name, {})
                    old_score_value = old_score_data.get("score", 0) if isinstance(old_score_data, dict) else 0

                    if abs(new_score.score - old_score_value) > 5:
                        rel.trait_evolution.append({
                            "timestamp": int(datetime.now(timezone.utc).timestamp()),
                            "trait": trait_name,
                            "old_score": old_score_value,
                            "new_score": new_score.score,
                            "evaluation_index": len(rel.evaluations) - 1,
                        })

                # Build trait_changes for SUMMARY block display
                trait_changes = {}
                assigned = []
                strengthened = []
                weakened = []

                for trait_name, new_score in new_trait_scores.items():
                    old_score_data = old_trait_scores.get(trait_name, {})
                    old_score_value = old_score_data.get("score", 0) if isinstance(old_score_data, dict) else 0

                    if trait_name not in old_trait_scores:
                        assigned.append(trait_name)
                    elif new_score.score > old_score_value + 3:
                        strengthened.append(trait_name)
                    elif new_score.score < old_score_value - 3:
                        weakened.append(trait_name)

                if assigned or strengthened or weakened:
                    trait_changes[entity_id] = {
                        "assigned": assigned,
                        "strengthened": strengthened,
                        "weakened": weakened,
                        "removed": [],
                    }

                # Update the evaluation record with trait changes
                if trait_changes and rel.evaluations:
                    rel.evaluations[-1]["trait_changes"] = trait_changes

                logger.debug("traits_detected", entity_id=entity_id,
                           trait_count=len(new_trait_scores),
                           confident_count=len([t for t in new_trait_scores.values() if t.is_confident]))

            except Exception as e:
                logger.error("trait_detection_failed", entity_id=entity_id, error=str(e))
```

#### Line ~1220: Enhance AI evaluation prompt

In the `_evaluate_relationships_with_ai` method, update the prompt to include the 6 new metrics and trait detection:

**ADD to the prompt (after the negative metrics section):**

```python
NEW COMMUNICATION/BEHAVIORAL METRICS (6 AI-evaluated, 0-100 scale):
- verbosity: How much do they write/talk? (0=terse, 100=very verbose)
- punctuality: Do they respond/show up on time? (0=always late, 100=always punctual)
- emotional_stability: How consistent is their emotional state? (0=volatile, 100=very stable)
- directness: How plainly do they communicate? (0=indirect/hints, 100=very direct)
- energy_level: What's their activity/engagement level? (0=low energy, 100=high energy)
- humor_style: What type of humor? (0=literal/serious, 50=balanced, 100=very sarcastic/playful)

TRAIT DETECTION (OPTIONAL but helpful):
If you can identify personality traits from this conversation, list them.
Examples: reliable, flirty, supportive, analytical, verbose, manipulative, patient, etc.

Return JSON with this structure:
{
  "entity_id_1": {
    "evaluation_summary": "Brief summary",
    "deltas": {
      // All 36 metrics
    },
    "reasoning": "Detailed explanation",
    "key_moments": ["Block X: event"],
    "detected_traits": ["trait1", "trait2"],  // NEW: Optional trait identification
    "trait_evidence": {  // NEW: Optional evidence for traits
      "trait1": "Evidence from conversation"
    }
  }
}
```

---

### 1.5 Modify: `config/trust_scoring.yaml`

**ADD at the end of the file:**

```yaml
# ============================================================
# TRAIT DETECTION SETTINGS
# ============================================================

trait_detection:
  # Base requirements (scaled by difficulty)
  base_evidence_required: 4      # Evaluations needed before confident
  confidence_threshold: 65.0     # Min score to display trait
  evolution_log_threshold: 5.0   # Min change to log in evolution
  max_traits_displayed: 8        # Limit on relationship card

  # Difficulty multipliers (applied to base_evidence_required)
  difficulty_multipliers:
    quick: 0.5     # 2 evals
    normal: 0.75   # 3 evals
    long: 1.0      # 4 evals
    extreme: 2.0   # 8 evals

  # Confidence growth rates per difficulty
  growth_rates:
    quick: 1.0     # Full growth
    normal: 0.8    # 80% growth
    long: 0.5      # 50% growth
    extreme: 0.2   # 20% growth

  # Trait decay - traits fade without reinforcement
  decay:
    enabled: true
    half_life_days:
      quick: 30
      normal: 60
      long: 90
      extreme: 180

  # Warning trait special handling
  warning_traits:
    evidence_required: 2         # Fewer evals needed
    confidence_threshold: 75.0   # Higher bar to confirm
    show_emerging: true          # Show below threshold as heads-up
    emerging_threshold: 40.0     # Min score to show as "emerging"

  # Volatility detection
  volatility:
    window_size: 5               # Recent scores to analyze
    high_volatility_threshold: 25.0  # Std dev above = volatile
```

---

### 1.6 New File: `config/trait_definitions.yaml`

**Create this file with all 80+ trait definitions:**

```yaml
# Trait Definitions Configuration
# Each trait maps to relationship metrics for detection

traits:
  # ============================================================
  # COMMUNICATION TRAITS
  # ============================================================

  articulate:
    category: communication
    description: "Expresses ideas clearly and effectively"
    icon: "💬"
    color: "#3b82f6"
    polarity: positive
    primary_metrics: [verbosity, directness]
    supporting_metrics: [engagement, depth]
    negative_indicators: []
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: inarticulate

  verbose:
    category: communication
    description: "Uses many words, writes lengthy messages"
    icon: "📝"
    color: "#6366f1"
    polarity: neutral
    primary_metrics: [verbosity]
    supporting_metrics: [engagement, openness]
    negative_indicators: []
    confidence_threshold: 70.0
    evidence_required: 3
    opposite_trait: terse

  terse:
    category: communication
    description: "Uses few words, brief and to the point"
    icon: "✂️"
    color: "#64748b"
    polarity: neutral
    primary_metrics: []
    supporting_metrics: [directness]
    negative_indicators: [verbosity]
    confidence_threshold: 70.0
    evidence_required: 3
    opposite_trait: verbose

  direct:
    category: communication
    description: "Says things plainly without hints"
    icon: "🎯"
    color: "#22c55e"
    polarity: positive
    primary_metrics: [directness, honesty]
    supporting_metrics: []
    negative_indicators: []
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: indirect

  responsive:
    category: communication
    description: "Replies quickly and attentively"
    icon: "⚡"
    color: "#eab308"
    polarity: positive
    primary_metrics: [responsiveness]
    supporting_metrics: [engagement]
    negative_indicators: []
    confidence_threshold: 70.0
    evidence_required: 3
    opposite_trait: unresponsive

  # ============================================================
  # SOCIAL/INTERPERSONAL TRAITS
  # ============================================================

  warm:
    category: social
    description: "Emotionally accessible and welcoming"
    icon: "🌞"
    color: "#f97316"
    polarity: positive
    primary_metrics: [warmth, affection]
    supporting_metrics: [friendliness, openness]
    negative_indicators: [antagonism]
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: cold

  supportive:
    category: social
    description: "Provides help and encouragement"
    icon: "🤝"
    color: "#22c55e"
    polarity: positive
    primary_metrics: [support, empowerment]
    supporting_metrics: [patience, understanding]
    negative_indicators: [dismissiveness]
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: dismissive

  empathetic:
    category: social
    description: "Shows understanding and emotional awareness"
    icon: "💜"
    color: "#a855f7"
    polarity: positive
    primary_metrics: [understanding, warmth]
    supporting_metrics: [patience, support]
    negative_indicators: [condescension, dismissiveness]
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: apathetic

  charming:
    category: social
    description: "Socially magnetic and likeable"
    icon: "✨"
    color: "#ec4899"
    polarity: positive
    primary_metrics: [humor, warmth, engagement]
    supporting_metrics: [friendliness]
    negative_indicators: [antagonism]
    confidence_threshold: 70.0
    evidence_required: 4
    opposite_trait: off-putting

  humble:
    category: social
    description: "Modest, not boastful"
    icon: "🙏"
    color: "#64748b"
    polarity: positive
    primary_metrics: [respect]
    supporting_metrics: [openness]
    negative_indicators: [condescension]
    confidence_threshold: 65.0
    evidence_required: 4
    opposite_trait: arrogant

  # ============================================================
  # RELIABILITY/TRUST TRAITS
  # ============================================================

  reliable:
    category: reliability
    description: "Consistently follows through on commitments"
    icon: "🎯"
    color: "#22c55e"
    polarity: positive
    primary_metrics: [reliability, honesty]
    supporting_metrics: [punctuality, responsiveness]
    negative_indicators: [betrayal]
    confidence_threshold: 70.0
    evidence_required: 4
    opposite_trait: flaky

  flaky:
    category: reliability
    description: "Inconsistent, doesn't follow through"
    icon: "💨"
    color: "#f97316"
    polarity: negative
    primary_metrics: []
    supporting_metrics: []
    negative_indicators: [reliability, punctuality]
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: reliable

  honest:
    category: reliability
    description: "Truthful and transparent"
    icon: "💎"
    color: "#06b6d4"
    polarity: positive
    primary_metrics: [honesty]
    supporting_metrics: [openness, directness]
    negative_indicators: [manipulation, betrayal]
    confidence_threshold: 70.0
    evidence_required: 4
    opposite_trait: deceptive

  trustworthy:
    category: reliability
    description: "Overall dependable and safe to trust"
    icon: "🛡️"
    color: "#22c55e"
    polarity: positive
    primary_metrics: [honesty, reliability, loyalty]
    supporting_metrics: [support, respect]
    negative_indicators: [betrayal, manipulation, distrust]
    confidence_threshold: 75.0
    evidence_required: 5
    opposite_trait: sketchy

  loyal:
    category: reliability
    description: "Stands by others through difficulties"
    icon: "🤞"
    color: "#8b5cf6"
    polarity: positive
    primary_metrics: [loyalty, support]
    supporting_metrics: [reliability]
    negative_indicators: [betrayal]
    confidence_threshold: 70.0
    evidence_required: 4
    opposite_trait: disloyal

  # ============================================================
  # EMOTIONAL TRAITS
  # ============================================================

  stable:
    category: emotional
    description: "Emotionally consistent and predictable"
    icon: "⚖️"
    color: "#22c55e"
    polarity: positive
    primary_metrics: [emotional_stability]
    supporting_metrics: [patience]
    negative_indicators: []
    confidence_threshold: 70.0
    evidence_required: 4
    opposite_trait: volatile

  volatile:
    category: emotional
    description: "Emotionally unpredictable"
    icon: "🌪️"
    color: "#ef4444"
    polarity: negative
    primary_metrics: []
    supporting_metrics: []
    negative_indicators: [emotional_stability, patience]
    confidence_threshold: 60.0
    evidence_required: 3
    opposite_trait: stable

  optimistic:
    category: emotional
    description: "Positive outlook on situations"
    icon: "☀️"
    color: "#eab308"
    polarity: positive
    primary_metrics: [warmth, humor]
    supporting_metrics: [engagement]
    negative_indicators: [resentment, antagonism]
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: pessimistic

  patient:
    category: emotional
    description: "Tolerant and understanding under stress"
    icon: "🕰️"
    color: "#64748b"
    polarity: positive
    primary_metrics: [patience]
    supporting_metrics: [understanding, support]
    negative_indicators: [annoyance, tension]
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: impatient

  # ============================================================
  # ENERGY/TEMPO TRAITS
  # ============================================================

  high-energy:
    category: energy
    description: "Active and enthusiastic"
    icon: "⚡"
    color: "#eab308"
    polarity: neutral
    primary_metrics: [energy_level, engagement]
    supporting_metrics: []
    negative_indicators: []
    confidence_threshold: 70.0
    evidence_required: 3
    opposite_trait: low-energy

  intense:
    category: energy
    description: "Highly engaged and focused"
    icon: "🔥"
    color: "#ef4444"
    polarity: neutral
    primary_metrics: [engagement, depth, energy_level]
    supporting_metrics: []
    negative_indicators: []
    confidence_threshold: 70.0
    evidence_required: 3
    opposite_trait: laid-back

  # ============================================================
  # INTELLECT/THINKING TRAITS
  # ============================================================

  analytical:
    category: intellect
    description: "Uses logical, systematic reasoning"
    icon: "🔬"
    color: "#3b82f6"
    polarity: positive
    primary_metrics: [expertise, depth]
    supporting_metrics: [directness]
    negative_indicators: []
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: intuitive

  curious:
    category: intellect
    description: "Shows interest in learning and exploring"
    icon: "🔍"
    color: "#8b5cf6"
    polarity: positive
    primary_metrics: [engagement, depth, openness]
    supporting_metrics: []
    negative_indicators: []
    confidence_threshold: 65.0
    evidence_required: 3
    opposite_trait: incurious

  creative:
    category: intellect
    description: "Shows novel thinking and ideas"
    icon: "🎨"
    color: "#ec4899"
    polarity: positive
    primary_metrics: [depth, humor]
    supporting_metrics: [openness, engagement]
    negative_indicators: []
    confidence_threshold: 70.0
    evidence_required: 4
    opposite_trait: conventional

  # ============================================================
  # WARNING TRAITS (Special handling: fewer evals, higher threshold)
  # ============================================================

  manipulative:
    category: warning
    description: "Uses others for personal gain through deception"
    icon: "🎭"
    color: "#ef4444"
    polarity: warning
    primary_metrics: [manipulation]
    supporting_metrics: [betrayal]
    negative_indicators: [honesty, loyalty]
    confidence_threshold: 75.0
    evidence_required: 2
    is_warning: true

  gaslighting:
    category: warning
    description: "Denies reality to confuse and control"
    icon: "💨"
    color: "#ef4444"
    polarity: warning
    primary_metrics: [manipulation, distrust]
    supporting_metrics: [condescension]
    negative_indicators: [honesty, support]
    confidence_threshold: 75.0
    evidence_required: 2
    is_warning: true

  toxic:
    category: warning
    description: "Generally harmful to interact with"
    icon: "☠️"
    color: "#ef4444"
    polarity: warning
    primary_metrics: [antagonism, manipulation]
    supporting_metrics: [resentment, condescension, dismissiveness]
    negative_indicators: [warmth, support, respect]
    confidence_threshold: 75.0
    evidence_required: 2
    is_warning: true

  narcissistic:
    category: warning
    description: "Excessive self-focus, lacks empathy"
    icon: "🪞"
    color: "#ef4444"
    polarity: warning
    primary_metrics: [condescension]
    supporting_metrics: [dismissiveness]
    negative_indicators: [understanding, humility, support]
    confidence_threshold: 75.0
    evidence_required: 3
    is_warning: true

  passive-aggressive:
    category: warning
    description: "Expresses hostility indirectly"
    icon: "😤"
    color: "#f97316"
    polarity: warning
    primary_metrics: [antagonism, resentment]
    supporting_metrics: [tension]
    negative_indicators: [directness, honesty]
    confidence_threshold: 70.0
    evidence_required: 2
    is_warning: true

  controlling:
    category: warning
    description: "Tries to dictate others' behavior"
    icon: "🎮"
    color: "#ef4444"
    polarity: warning
    primary_metrics: [condescension, manipulation]
    supporting_metrics: [antagonism]
    negative_indicators: [respect, empowerment]
    confidence_threshold: 75.0
    evidence_required: 2
    is_warning: true

  two-faced:
    category: warning
    description: "Different behavior to different people"
    icon: "🎭"
    color: "#f97316"
    polarity: warning
    primary_metrics: [manipulation]
    supporting_metrics: [distrust]
    negative_indicators: [honesty, consistency]
    confidence_threshold: 70.0
    evidence_required: 3
    is_warning: true
```

---

## PART 2: FRONTEND CHANGES

### 2.1 Update: `RelationshipsTab.tsx` TypeScript Interface

**Location**: Lines 17-78

**ADD these fields to the `Relationship` interface:**

```typescript
interface Relationship {
  // ... existing fields ...

  // NEW: 6 additional metrics
  verbosity: number;
  punctuality: number;
  emotional_stability: number;
  directness: number;
  energy_level: number;
  humor_style: number;

  // NEW: Trait fields
  trait_scores: Record<string, TraitScore>;
  trait_evolution: TraitEvolutionEntry[];
  manual_trait_overrides: Record<string, boolean>;
  trait_scores_version: string;
}

// NEW: Add these interfaces after Relationship
interface TraitScore {
  score: number;
  evidence_count: number;
  first_detected: number;
  last_updated: number;
  consistency: number;
  volatility: number;
  trend: 'rising' | 'stable' | 'falling';
  source: 'metric_derived' | 'ai_direct' | 'both';
  is_confident: boolean;
}

interface TraitEvolutionEntry {
  timestamp: number;
  trait: string;
  old_score: number;
  new_score: number;
  evaluation_index: number;
}

interface TraitDefinition {
  name: string;
  category: string;
  description: string;
  icon: string;
  color: string;
  polarity: 'positive' | 'negative' | 'neutral' | 'warning';
  is_warning?: boolean;
}
```

### 2.2 New Component: `TraitBadges.tsx`

**Create**: `qubes-gui/src/components/relationships/TraitBadges.tsx`

```tsx
import React from 'react';

interface TraitScore {
  score: number;
  evidence_count: number;
  volatility: number;
  trend: 'rising' | 'stable' | 'falling';
  is_confident: boolean;
}

interface TraitDefinition {
  name: string;
  description: string;
  icon: string;
  color: string;
  polarity: 'positive' | 'negative' | 'neutral' | 'warning';
  is_warning?: boolean;
}

interface TraitBadgesProps {
  traitScores: Record<string, TraitScore>;
  traitDefinitions: Record<string, TraitDefinition>;
  maxDisplay?: number;
  showEmerging?: boolean;
  onRemoveTrait?: (trait: string) => void;
}

const WARNING_TRAITS = [
  'manipulative', 'gaslighting', 'toxic', 'narcissistic',
  'passive-aggressive', 'controlling', 'two-faced'
];

export const TraitBadges: React.FC<TraitBadgesProps> = ({
  traitScores,
  traitDefinitions,
  maxDisplay = 8,
  showEmerging = true,
  onRemoveTrait,
}) => {
  // Sort traits: warning first, then by confidence
  const sortedTraits = Object.entries(traitScores)
    .filter(([name, score]) => {
      if (score.is_confident) return true;
      if (showEmerging && score.score >= 40) return true;
      return false;
    })
    .sort(([aName, aScore], [bName, bScore]) => {
      const aWarning = WARNING_TRAITS.includes(aName) ? 1 : 0;
      const bWarning = WARNING_TRAITS.includes(bName) ? 1 : 0;
      if (aWarning !== bWarning) return bWarning - aWarning;
      return bScore.score - aScore.score;
    })
    .slice(0, maxDisplay);

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'rising': return '↑';
      case 'falling': return '↓';
      default: return '';
    }
  };

  const getOpacityClass = (score: TraitScore) => {
    if (score.is_confident && score.score >= 75) return 'opacity-100';
    if (score.is_confident) return 'opacity-90';
    return 'opacity-60';  // Emerging
  };

  return (
    <div className="flex flex-wrap gap-1.5">
      {sortedTraits.map(([name, score]) => {
        const def = traitDefinitions[name];
        const isWarning = WARNING_TRAITS.includes(name);

        const bgClass = isWarning
          ? 'bg-red-500/20 border-red-500/40'
          : score.is_confident
            ? 'bg-accent-primary/20 border-accent-primary/40'
            : 'bg-gray-500/20 border-gray-500/40';

        const textClass = isWarning
          ? 'text-red-400'
          : score.is_confident
            ? 'text-accent-primary'
            : 'text-gray-400';

        return (
          <span
            key={name}
            className={`
              inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs
              border ${bgClass} ${textClass} ${getOpacityClass(score)}
              transition-all hover:brightness-110
            `}
            title={`${def?.description || name}\nConfidence: ${score.score.toFixed(0)}%\nEvidence: ${score.evidence_count} evaluations`}
          >
            <span>{def?.icon || '🏷️'}</span>
            <span>{name}</span>
            <span className="text-[10px] opacity-70">
              {score.score.toFixed(0)}%
            </span>
            {score.volatility > 25 && (
              <span className="text-yellow-400" title="Volatile/inconsistent">⚡</span>
            )}
            {getTrendIcon(score.trend) && (
              <span className={score.trend === 'rising' ? 'text-green-400' : 'text-orange-400'}>
                {getTrendIcon(score.trend)}
              </span>
            )}
            {!score.is_confident && (
              <span className="text-[9px] text-gray-500">(emerging)</span>
            )}
            {onRemoveTrait && (
              <button
                onClick={(e) => { e.stopPropagation(); onRemoveTrait(name); }}
                className="ml-0.5 hover:text-red-400 transition-colors"
              >
                ×
              </button>
            )}
          </span>
        );
      })}

      {sortedTraits.length === 0 && (
        <span className="text-text-tertiary text-xs italic">
          No traits detected yet
        </span>
      )}
    </div>
  );
};
```

### 2.3 Update: `TagManager.tsx` to `TraitManager.tsx`

**Rename** `TagManager.tsx` to `TraitManager.tsx` and update:

```tsx
import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { TraitBadges } from './TraitBadges';

interface TraitScore {
  score: number;
  evidence_count: number;
  volatility: number;
  trend: 'rising' | 'stable' | 'falling';
  is_confident: boolean;
}

interface TraitDefinition {
  name: string;
  description: string;
  icon: string;
  color: string;
  polarity: string;
}

interface TraitManagerProps {
  entityId: string;
  traitScores: Record<string, TraitScore>;
  traitDefinitions: Record<string, TraitDefinition>;
  manualOverrides: Record<string, boolean>;
  qubeId: string;
  userId: string;
  password: string;
  onTraitOverride: (trait: string, visible: boolean) => void;
  disabled?: boolean;
}

export const TraitManager: React.FC<TraitManagerProps> = ({
  entityId,
  traitScores,
  traitDefinitions,
  manualOverrides,
  qubeId,
  userId,
  password,
  onTraitOverride,
  disabled = false,
}) => {
  // Filter out manually hidden traits
  const visibleTraits: Record<string, TraitScore> = {};
  for (const [name, score] of Object.entries(traitScores)) {
    if (manualOverrides[name] !== false) {
      visibleTraits[name] = score;
    }
  }

  const handleRemoveTrait = (trait: string) => {
    onTraitOverride(trait, false);
  };

  return (
    <div className="space-y-2">
      <h4 className="text-text-secondary font-semibold text-xs flex items-center gap-1">
        🧬 Traits
        <span className="text-text-tertiary font-normal">(AI-detected)</span>
      </h4>

      <TraitBadges
        traitScores={visibleTraits}
        traitDefinitions={traitDefinitions}
        onRemoveTrait={disabled ? undefined : handleRemoveTrait}
      />
    </div>
  );
};
```

### 2.4 Update: `BlocksTab.tsx` for SUMMARY trait display

**Location**: Around lines 1473-1562 (relationships_affected section)

**ADD after the existing relationships section:**

```tsx
{/* Trait Changes Section */}
{selectedBlock.block_type === 'SUMMARY' &&
 decryptedContent?.relationships_affected &&
 Object.values(decryptedContent.relationships_affected).some(
   (r: any) => r.trait_changes
 ) && (
  <div className="mt-4 pt-4 border-t border-glass-border">
    <h4 className="text-text-primary text-sm font-semibold mb-3 flex items-center gap-2">
      🧬 Trait Changes
    </h4>
    {Object.entries(decryptedContent.relationships_affected).map(([entityId, data]: [string, any]) => {
      const changes = data.trait_changes?.[entityId];
      if (!changes) return null;

      const hasChanges = changes.assigned?.length || changes.strengthened?.length ||
                        changes.weakened?.length || changes.removed?.length;
      if (!hasChanges) return null;

      return (
        <div key={entityId} className="mb-3">
          <span className="text-text-secondary text-xs font-medium">{entityId}:</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {changes.assigned?.map((trait: string) => (
              <span key={trait} className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded-full">
                +{trait} (NEW)
              </span>
            ))}
            {changes.strengthened?.map((trait: string) => (
              <span key={trait} className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded-full">
                ↑{trait}
              </span>
            ))}
            {changes.weakened?.map((trait: string) => (
              <span key={trait} className="px-2 py-0.5 text-xs bg-orange-500/20 text-orange-400 rounded-full">
                ↓{trait}
              </span>
            ))}
            {changes.removed?.map((trait: string) => (
              <span key={trait} className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 rounded-full line-through">
                {trait}
              </span>
            ))}
          </div>
        </div>
      );
    })}
  </div>
)}
```

---

## PART 3: RUST/TAURI CHANGES

### 3.1 Update: `lib.rs` - Add TraitData struct

**Location**: After `TagData` struct (around line 616)

```rust
#[derive(Debug, Serialize, Deserialize)]
struct TraitScoreData {
    score: f64,
    evidence_count: i32,
    first_detected: i64,
    last_updated: i64,
    consistency: f64,
    volatility: f64,
    trend: String,
    source: String,
    is_confident: bool,
}

#[derive(Debug, Serialize, Deserialize)]
struct TraitDefinitionData {
    name: String,
    category: String,
    description: String,
    icon: String,
    color: String,
    polarity: String,
    is_warning: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize)]
struct TraitDefinitionsResponse {
    success: bool,
    traits: Option<std::collections::HashMap<String, TraitDefinitionData>>,
    error: Option<String>,
}
```

### 3.2 Add new Tauri command: `get_trait_definitions`

**Location**: After `get_available_tags` command

```rust
#[tauri::command]
async fn get_trait_definitions(
    user_id: String,
    qube_id: String,
) -> Result<TraitDefinitionsResponse, String> {
    let output = run_python_command(&[
        "get-trait-definitions",
        &user_id,
        &qube_id,
    ]).await?;

    parse_json_response(&output)
}
```

### 3.3 Register new command

**Location**: In `invoke_handler!` macro (around line 5168)

Add `get_trait_definitions` to the list of commands.

---

## PART 4: IMPLEMENTATION ORDER

### Phase 1: Backend Foundation
1. Create `utils/trait_definitions.py`
2. Create `config/trait_definitions.yaml`
3. Create `relationships/trait_detection.py`
4. Update `config/trust_scoring.yaml`

### Phase 2: Relationship Integration
5. Update `relationships/relationship.py` (add fields, serialization)
6. Update `core/session.py` (integrate trait detection)

### Phase 3: Frontend Display
7. Create `TraitBadges.tsx`
8. Refactor `TagManager.tsx` to `TraitManager.tsx`
9. Update `RelationshipsTab.tsx` (use TraitManager)
10. Update `BlocksTab.tsx` (show trait changes in SUMMARY)

### Phase 4: Tauri Bridge
11. Update `lib.rs` (add structs and command)
12. Update `gui_bridge.py` (add CLI command)

### Phase 5: Testing
13. Test trait detection with sample conversations
14. Verify SUMMARY blocks show trait changes
15. Test difficulty scaling

---

## Verification Checklist

- [ ] `TraitScore` dataclass works in relationship serialization
- [ ] Traits persist in `relationships.json`
- [ ] `TraitDetector` calculates scores from metrics
- [ ] AI evaluation includes 6 new metrics
- [ ] SUMMARY blocks show trait changes
- [ ] `TraitBadges` displays confident and emerging traits
- [ ] Warning traits highlighted appropriately
- [ ] Difficulty settings scale evidence requirements
- [ ] Volatility indicator (⚡) shows for unstable traits
