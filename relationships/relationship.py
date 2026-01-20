"""
Relationship Data Structures

Manages relationship records between Qubes and humans with AI-driven evaluation.
From docs/RELATIONSHIP_SCHEMA_FINAL_2025-11-02.md
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import json

from utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# RELATIONSHIP STATUS SYSTEM
# =============================================================================

# Relationship status definitions with numeric values for ordering
RELATIONSHIP_STATUSES = {
    # Negative statuses
    "blocked": -100,      # No contact allowed
    "enemy": -50,         # Hostile relationship
    "rival": -20,         # Competitive/adversarial
    "suspicious": -10,    # Red flags, uncertain

    # Neutral/Positive statuses
    "unmet": 0,           # Never met (default)
    "stranger": 5,        # Met but minimal history
    "acquaintance": 20,   # Familiar, developing
    "friend": 50,         # Positive relationship
    "close_friend": 75,   # Strong bond
    "best_friend": 100,   # Maximum friendship (only one)
}

# Valid status transitions (status -> list of valid next statuses)
# Owner/system can force any transition; organic progression follows these rules
VALID_STATUS_TRANSITIONS = {
    "blocked": [],  # Only owner can unblock
    "enemy": ["blocked", "rival", "suspicious"],
    "rival": ["enemy", "suspicious", "stranger"],
    "suspicious": ["rival", "stranger", "acquaintance"],
    "unmet": ["stranger"],  # First contact
    "stranger": ["suspicious", "acquaintance"],
    "acquaintance": ["suspicious", "stranger", "friend"],
    "friend": ["suspicious", "acquaintance", "close_friend"],
    "close_friend": ["friend", "best_friend"],
    "best_friend": ["close_friend"],  # Can only demote one step
}

# Betrayal causes dramatic status drops
BETRAYAL_TARGET_STATUS = {
    "best_friend": "suspicious",
    "close_friend": "suspicious",
    "friend": "rival",
    "acquaintance": "suspicious",
    "stranger": "suspicious",
}


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


class Relationship:
    """
    Relationship data model with 30 AI-evaluated metrics

    Structure:
    - 5 Core Trust Metrics (5 AI-evaluated + 1 calculated)
    - 14 Positive Social Metrics (AI-evaluated)
    - 10 Negative Social Metrics (AI-evaluated)
    - 9 Tracked Statistics (auto-incremented)
    - 4 Essential Identity
    - 5 Relationship State

    Total: 48 fields
    """

    def __init__(
        self,
        entity_id: str,
        entity_type: str = "qube",
        public_key: Optional[str] = None,
        has_met: bool = False,
        is_creator: bool = False,
        entity_name: Optional[str] = None,  # Optional: Entity's display name for search
        nft_address: Optional[str] = None,  # DEPRECATED: Kept for backward compatibility
        **kwargs  # Absorb any other deprecated fields
    ):
        """
        Initialize a new relationship

        Args:
            entity_id: Qube ID or human ID
            entity_type: "qube" or "human"
            public_key: Public key of entity
            has_met: Whether direct interaction has occurred
            is_creator: Whether this entity is the qube's creator (starts metrics at 25)
            entity_name: Optional display name for this entity (for name-based lookup)
        """
        # Essential Identity (5) - Added entity_name
        self.relationship_id = f"rel-{uuid.uuid4()}"
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.public_key = public_key
        self.entity_name = entity_name  # Store entity name for search
        self.is_creator = is_creator    # Whether this is the qube's creator

        # Core Trust Metrics (6) - 5 AI-evaluated + 1 calculated
        self.honesty = 0.0              # 0-100, how truthful/transparent
        self.reliability = 0.0          # 0-100, how dependable/consistent
        self.support = 0.0              # 0-100, emotional/practical help provided
        self.loyalty = 0.0              # 0-100, commitment to relationship
        self.respect = 0.0              # 0-100, regard, admiration, valuing them
        self.trust = 0.0                # 0-100, CALCULATED from above 5

        # Social Metrics - Positive (14 total) - AI evaluates all
        self.friendship = 0.0           # 0-100, warmth, friendliness, camaraderie
        self.affection = 0.0            # 0-100, emotional connection, caring
        self.engagement = 0.0           # 0-100, investment in conversations
        self.depth = 0.0                # 0-100, meaningful vs superficial exchanges
        self.humor = 0.0                # 0-100, playfulness, fun, levity
        self.understanding = 0.0        # 0-100, empathy, listening, comprehension
        self.compatibility = 0.0        # 0-100, personality/style alignment
        self.admiration = 0.0           # 0-100, looking up to them, respect achievements
        self.warmth = 0.0               # 0-100, emotional warmth, kindness, gentleness
        self.openness = 0.0             # 0-100, vulnerability, sharing personal things
        self.patience = 0.0             # 0-100, tolerance, understanding under stress
        self.empowerment = 0.0          # 0-100, they help you grow/improve
        self.responsiveness = 0.0       # 0-100, how quickly they respond
        self.expertise = 0.0            # 0-100, knowledge/competence level

        # Social Metrics - Negative (10 total) - AI evaluates all
        self.antagonism = 0.0           # 0-100, active hostility, opposition
        self.resentment = 0.0           # 0-100, bitterness, grudges held
        self.annoyance = 0.0            # 0-100, irritation, minor frustrations
        self.distrust = 0.0             # 0-100, suspicion, doubt, lack of confidence
        self.rivalry = 0.0              # 0-100, competitive tension
        self.tension = 0.0              # 0-100, unresolved conflict, awkwardness
        self.condescension = 0.0        # 0-100, talking down, patronizing
        self.manipulation = 0.0         # 0-100, deceptive tactics, using you
        self.dismissiveness = 0.0       # 0-100, invalidation, not taking seriously
        self.betrayal = 0.0             # 0-100, major broken trust events

        # Behavioral/Communication Metrics (6 total) - AI evaluates for trait detection
        self.verbosity = 0.0            # 0-100, how much they write/talk (0=terse, 100=verbose)
        self.punctuality = 0.0          # 0-100, do they respond/show up on time
        self.emotional_stability = 0.0  # 0-100, consistency of emotional state
        self.directness = 0.0           # 0-100, how plainly they communicate (0=indirect, 100=direct)
        self.energy_level = 0.0         # 0-100, activity/engagement level
        self.humor_style = 50.0         # 0-100, type of humor (0=literal/serious, 50=balanced, 100=sarcastic)

        # Tracked Statistics (9) - auto-incremented, not AI-evaluated
        self.messages_sent = 0          # Outgoing message count
        self.messages_received = 0      # Incoming message count
        self.response_time_avg = 0.0    # Average response time (seconds)
        self.last_interaction: Optional[int] = None  # Unix timestamp
        self.collaborations = 0         # Total collaboration count
        self.collaborations_successful = 0  # Successful joint tasks
        self.collaborations_failed = 0  # Failed joint tasks
        self.first_contact: Optional[int] = None if not has_met else int(datetime.now(timezone.utc).timestamp())
        self.days_known = 0             # Days since first contact (calculated)

        # Relationship State (5)
        self.has_met = has_met
        self.status = "unmet" if not has_met else "stranger"  # unmet/stranger/acquaintance/friend/close_friend/best_friend
        self.is_best_friend = False     # Special designation (only one allowed)
        self.progression_history: List[Dict[str, Any]] = [
            {
                "status": self.status,
                "timestamp": int(datetime.now(timezone.utc).timestamp())
            }
        ]

        # AI Evaluation History (1)
        self.evaluations: List[Dict[str, Any]] = []  # AI evaluation summaries with reasoning

        # Clearance (Phase 2 v2) - Access rights separate from relationship status
        self.clearance_profile: str = "none"  # Profile name from ClearanceConfig
        self.clearance_categories: List[str] = []  # Empty = all categories for level
        self.clearance_fields: List[str] = []  # Empty = all fields for categories
        self.clearance_expires: Optional[int] = None  # Unix timestamp, None = never
        self.clearance_granted_by: Optional[str] = None  # "owner" or entity_id
        self.clearance_granted_at: Optional[int] = None  # Unix timestamp
        # Per-entity overrides
        self.clearance_field_grants: List[str] = []  # Extra fields to allow
        self.clearance_field_denials: List[str] = []  # Fields to block
        # Tags (Phase 2 v2) - Relationship labels orthogonal to status
        self.tags: List[str] = []

        # Traits - AI-attributed personality/behavioral characteristics
        self.trait_scores: Dict[str, Any] = {}  # trait_name -> TraitScore dict
        self.trait_evolution: List[Dict[str, Any]] = []  # Timeline of changes
        self.manual_trait_overrides: Dict[str, bool] = {}  # User overrides (False = hidden)
        self.trait_scores_version: str = "1.0"  # For migration

        # Owner relationship: Special permanent status, standard starting metrics
        # Metrics start at 25 like everyone else, but status is always "owner"
        if is_creator:
            # Core Trust Metrics - Start at 25 (standard baseline)
            self.honesty = 25.0
            self.reliability = 25.0
            self.support = 25.0
            self.loyalty = 25.0
            self.respect = 25.0

            # Positive Social Metrics - Start at 25 (standard baseline)
            self.friendship = 25.0
            self.affection = 25.0
            self.engagement = 25.0
            self.depth = 25.0
            self.humor = 25.0
            self.understanding = 25.0
            self.compatibility = 25.0
            self.admiration = 25.0
            self.warmth = 25.0
            self.openness = 25.0
            self.patience = 25.0
            self.empowerment = 25.0
            self.responsiveness = 25.0
            self.expertise = 25.0

            # Update trust score based on core trust values
            self.trust = self.calculate_trust_score()

            # Owner has permanent "owner" status - doesn't progress like other relationships
            self.status = "owner"
            self.progression_history = [
                {
                    "status": "owner",
                    "timestamp": int(datetime.now(timezone.utc).timestamp()),
                    "reason": "Creator/owner relationship"
                }
            ]

            # Creators get elevated clearance (trusted profile by default)
            self.clearance_profile = "trusted"
            self.clearance_granted_by = "system"
            self.clearance_granted_at = int(datetime.now(timezone.utc).timestamp())

            logger.info(
                "creator_relationship_initialized",
                entity_id=entity_id,
                trust=self.trust,
                clearance_profile=self.clearance_profile
            )

        # Warn about deprecated fields
        if nft_address:
            logger.warning(
                "deprecated_nft_address_ignored",
                entity_id=entity_id,
                nft_address=nft_address
            )
        if kwargs:
            logger.warning(
                "deprecated_relationship_fields_ignored",
                entity_id=entity_id,
                deprecated_fields=list(kwargs.keys())
            )

        logger.info(
            "relationship_created",
            relationship_id=self.relationship_id,
            entity_id=entity_id,
            entity_type=entity_type,
            has_met=has_met
        )

    def calculate_trust_score(self) -> float:
        """
        Calculate trust from 5 core components:
        - honesty: 25% (foundation of trust)
        - reliability: 25% (can you count on them)
        - support: 20% (do they have your back)
        - loyalty: 15% (commitment to relationship)
        - respect: 15% (mutual regard and value)

        Returns:
            Trust score 0-100
        """
        trust = (
            self.honesty * 0.25 +
            self.reliability * 0.25 +
            self.support * 0.20 +
            self.loyalty * 0.15 +
            self.respect * 0.15
        )
        return max(0.0, min(100.0, trust))

    def update_trust_score(self) -> None:
        """Recalculate and update trust score"""
        self.trust = self.calculate_trust_score()

    def update_days_known(self) -> None:
        """Calculate days since first contact"""
        if self.first_contact:
            now = int(datetime.now(timezone.utc).timestamp())
            seconds_known = now - self.first_contact
            self.days_known = int(seconds_known / 86400)  # Convert to days
        else:
            self.days_known = 0

    # =========================================================================
    # STATUS VALIDATION METHODS
    # =========================================================================

    def get_status_value(self) -> int:
        """Get numeric value of current status for comparison."""
        return RELATIONSHIP_STATUSES.get(self.status, 0)

    def can_transition_to(self, new_status: str) -> bool:
        """
        Check if status transition is valid per organic progression rules.

        Args:
            new_status: Target status

        Returns:
            True if transition is allowed organically
        """
        if new_status not in RELATIONSHIP_STATUSES:
            return False

        valid_transitions = VALID_STATUS_TRANSITIONS.get(self.status, [])
        return new_status in valid_transitions

    def is_negative_status(self) -> bool:
        """Check if current status is negative (blocked, enemy, rival, suspicious)."""
        return self.get_status_value() < 0

    def is_blocked(self) -> bool:
        """Check if entity is blocked."""
        return self.status == "blocked"

    def apply_decay(self) -> bool:
        """
        Apply relationship decay for inactive relationships

        Decay rules for POSITIVE metrics:
        - Only applies after 30 days of inactivity
        - Heavy decay: Emotional warmth (friendship, affection, understanding, warmth)
        - Medium decay: Vulnerability/growth (engagement, openness, empowerment, responsiveness)
        - Light decay: Personal qualities (depth, humor, compatibility, admiration, patience, expertise)
        - NO decay: Core Trust (honesty, reliability, support, loyalty, respect) - earned through experience

        Decay rules for NEGATIVE metrics:
        - Fast decay: Temporary irritations (annoyance, tension, dismissiveness)
        - Medium decay: Lingering negativity (antagonism, rivalry)
        - Slow decay: Deep-seated issues (resentment, distrust, condescension, manipulation)
        - NO decay: Major violations (betrayal - permanent memory)

        Returns:
            True if decay was applied, False otherwise
        """
        if not self.last_interaction:
            return False

        now = int(datetime.now(timezone.utc).timestamp())
        days_inactive = (now - self.last_interaction) / 86400

        # Only apply decay after 30 days of inactivity
        if days_inactive <= 30:
            return False

        # Calculate decay factor using exponential decay
        # After 30 days: starts decaying
        # Formula: 0.98^(days - 30) means ~18% loss after 1 month, ~39% after 2 months
        excess_days = days_inactive - 30
        decay_factor = 0.98 ** excess_days

        # ===== POSITIVE METRICS DECAY (reduces positive feelings) =====

        # Heavy decay - emotional warmth fades without interaction
        self.friendship = max(0.0, self.friendship * decay_factor)
        self.affection = max(0.0, self.affection * decay_factor)
        self.understanding = max(0.0, self.understanding * decay_factor)
        self.warmth = max(0.0, self.warmth * decay_factor)

        # Medium decay - active engagement and vulnerability fade
        medium_decay = decay_factor ** 0.7
        self.engagement = max(0.0, self.engagement * medium_decay)
        self.openness = max(0.0, self.openness * medium_decay)
        self.empowerment = max(0.0, self.empowerment * medium_decay)
        self.responsiveness = max(0.0, self.responsiveness * medium_decay)

        # Light decay - personal qualities and assessments stick around longer
        light_decay = decay_factor ** 0.5
        self.depth = max(0.0, self.depth * light_decay)
        self.humor = max(0.0, self.humor * light_decay)
        self.compatibility = max(0.0, self.compatibility * light_decay)
        self.admiration = max(0.0, self.admiration * light_decay)
        self.patience = max(0.0, self.patience * light_decay)
        self.expertise = max(0.0, self.expertise * light_decay)

        # NO decay on Core Trust - these are earned through experience and define the foundation
        # honesty, reliability, support, loyalty, respect

        # ===== NEGATIVE METRICS DECAY (reduces negative feelings - healing) =====

        # Fast decay - temporary irritations fade quickly (good!)
        fast_negative_decay = decay_factor ** 1.5  # Faster than positive decay
        self.annoyance = max(0.0, self.annoyance * fast_negative_decay)
        self.tension = max(0.0, self.tension * fast_negative_decay)
        self.dismissiveness = max(0.0, self.dismissiveness * fast_negative_decay)

        # Medium decay - lingering negativity fades moderately
        medium_negative_decay = decay_factor
        self.antagonism = max(0.0, self.antagonism * medium_negative_decay)
        self.rivalry = max(0.0, self.rivalry * medium_negative_decay)

        # Slow decay - deep-seated issues linger
        slow_negative_decay = decay_factor ** 0.6
        self.resentment = max(0.0, self.resentment * slow_negative_decay)
        self.distrust = max(0.0, self.distrust * slow_negative_decay)
        self.condescension = max(0.0, self.condescension * slow_negative_decay)
        self.manipulation = max(0.0, self.manipulation * slow_negative_decay)

        # NO decay on betrayal - major broken trust events are permanent memories
        # betrayal stays at its current level

        # Recalculate trust score after decay
        self.update_trust_score()

        logger.info(
            "relationship_decay_applied",
            entity_id=self.entity_id,
            days_inactive=int(days_inactive),
            decay_factor=decay_factor,
            new_friendship=self.friendship,
            new_trust=self.trust
        )

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary for JSON serialization"""
        return {
            # Essential Identity (6)
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "relationship_id": self.relationship_id,
            "public_key": self.public_key,
            "entity_name": self.entity_name,
            "is_creator": self.is_creator,

            # Core Trust Metrics (5)
            "reliability": self.reliability,
            "honesty": self.honesty,
            "responsiveness": self.responsiveness,
            "expertise": self.expertise,
            "trust": self.trust,

            # Social Metrics - Positive (15)
            "friendship": self.friendship,
            "affection": self.affection,
            "respect": self.respect,
            "loyalty": self.loyalty,
            "support": self.support,
            "engagement": self.engagement,
            "depth": self.depth,
            "humor": self.humor,
            "understanding": self.understanding,
            "compatibility": self.compatibility,
            "admiration": self.admiration,
            "warmth": self.warmth,
            "openness": self.openness,
            "patience": self.patience,
            "empowerment": self.empowerment,

            # Social Metrics - Negative (10)
            "antagonism": self.antagonism,
            "resentment": self.resentment,
            "annoyance": self.annoyance,
            "distrust": self.distrust,
            "rivalry": self.rivalry,
            "tension": self.tension,
            "condescension": self.condescension,
            "manipulation": self.manipulation,
            "dismissiveness": self.dismissiveness,
            "betrayal": self.betrayal,

            # Behavioral/Communication Metrics (6)
            "verbosity": self.verbosity,
            "punctuality": self.punctuality,
            "emotional_stability": self.emotional_stability,
            "directness": self.directness,
            "energy_level": self.energy_level,
            "humor_style": self.humor_style,

            # Tracked Statistics (9)
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "response_time_avg": self.response_time_avg,
            "last_interaction": self.last_interaction,
            "collaborations": self.collaborations,
            "collaborations_successful": self.collaborations_successful,
            "collaborations_failed": self.collaborations_failed,
            "first_contact": self.first_contact,
            "days_known": self.days_known,

            # Relationship State (5)
            "has_met": self.has_met,
            "status": self.status,
            "is_best_friend": self.is_best_friend,
            "progression_history": self.progression_history,
            "evaluations": self.evaluations,

            # Clearance (10)
            "clearance_profile": self.clearance_profile,
            "clearance_categories": self.clearance_categories,
            "clearance_fields": self.clearance_fields,
            "clearance_expires": self.clearance_expires,
            "clearance_granted_by": self.clearance_granted_by,
            "clearance_granted_at": self.clearance_granted_at,
            "clearance_field_grants": self.clearance_field_grants,
            "clearance_field_denials": self.clearance_field_denials,

            # Tags (1)
            "tags": self.tags,

            # Traits (4)
            "trait_scores": {
                name: (ts.to_dict() if hasattr(ts, 'to_dict') else ts)
                for name, ts in self.trait_scores.items()
            },
            "trait_evolution": self.trait_evolution,
            "manual_trait_overrides": self.manual_trait_overrides,
            "trait_scores_version": self.trait_scores_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """Load relationship from dictionary"""
        rel = cls(
            entity_id=data["entity_id"],
            entity_type=data.get("entity_type", "qube"),
            public_key=data.get("public_key"),
            has_met=data.get("has_met", False),
            entity_name=data.get("entity_name"),
            is_creator=data.get("is_creator", False)
        )

        # Override generated ID with stored one
        rel.relationship_id = data.get("relationship_id", rel.relationship_id)

        # Core Trust Metrics (5)
        rel.reliability = data.get("reliability", 0.0)
        rel.honesty = data.get("honesty", 0.0)
        rel.responsiveness = data.get("responsiveness", 0.0)
        rel.expertise = data.get("expertise", 0.0)
        rel.trust = data.get("trust", 0.0)

        # Social Metrics - Positive (15)
        rel.friendship = data.get("friendship", 0.0)
        rel.affection = data.get("affection", 0.0)
        rel.respect = data.get("respect", 0.0)
        rel.loyalty = data.get("loyalty", 0.0)
        rel.support = data.get("support", 0.0)
        rel.engagement = data.get("engagement", 0.0)
        rel.depth = data.get("depth", 0.0)
        rel.humor = data.get("humor", 0.0)
        rel.understanding = data.get("understanding", 0.0)
        rel.compatibility = data.get("compatibility", 0.0)
        rel.admiration = data.get("admiration", 0.0)
        rel.warmth = data.get("warmth", 0.0)
        rel.openness = data.get("openness", 0.0)
        rel.patience = data.get("patience", 0.0)
        rel.empowerment = data.get("empowerment", 0.0)

        # Social Metrics - Negative (10)
        rel.antagonism = data.get("antagonism", 0.0)
        rel.resentment = data.get("resentment", 0.0)
        rel.annoyance = data.get("annoyance", 0.0)
        rel.distrust = data.get("distrust", 0.0)
        rel.rivalry = data.get("rivalry", 0.0)
        rel.tension = data.get("tension", 0.0)
        rel.condescension = data.get("condescension", 0.0)
        rel.manipulation = data.get("manipulation", 0.0)
        rel.dismissiveness = data.get("dismissiveness", 0.0)
        rel.betrayal = data.get("betrayal", 0.0)

        # Behavioral/Communication Metrics (6)
        rel.verbosity = data.get("verbosity", 0.0)
        rel.punctuality = data.get("punctuality", 0.0)
        rel.emotional_stability = data.get("emotional_stability", 0.0)
        rel.directness = data.get("directness", 0.0)
        rel.energy_level = data.get("energy_level", 0.0)
        rel.humor_style = data.get("humor_style", 50.0)

        # Tracked Statistics (9)
        rel.messages_sent = data.get("messages_sent", 0)
        rel.messages_received = data.get("messages_received", 0)
        rel.response_time_avg = data.get("response_time_avg", 0.0)
        rel.last_interaction = data.get("last_interaction")
        rel.collaborations = data.get("collaborations", 0)
        rel.collaborations_successful = data.get("collaborations_successful", 0)
        rel.collaborations_failed = data.get("collaborations_failed", 0)
        rel.first_contact = data.get("first_contact")
        rel.days_known = data.get("days_known", 0)

        # Relationship State (5)
        rel.status = data.get("status", "unmet")
        rel.is_best_friend = data.get("is_best_friend", False)
        rel.progression_history = data.get("progression_history", [])
        rel.evaluations = data.get("evaluations", [])

        # Clearance (10) - with migration from old clearance_level
        if "clearance_profile" in data:
            rel.clearance_profile = data["clearance_profile"]
        elif "clearance_level" in data:
            # Migration: clearance_level -> clearance_profile
            old_level = data["clearance_level"]
            migration_map = {
                "none": "none",
                "public": "public",
                "private": "trusted",
                "secret": "inner_circle",
            }
            rel.clearance_profile = migration_map.get(old_level, "none")
        else:
            rel.clearance_profile = "none"
        rel.clearance_categories = data.get("clearance_categories", [])
        rel.clearance_fields = data.get("clearance_fields", [])
        rel.clearance_expires = data.get("clearance_expires")
        rel.clearance_granted_by = data.get("clearance_granted_by")
        rel.clearance_granted_at = data.get("clearance_granted_at")
        rel.clearance_field_grants = data.get("clearance_field_grants", [])
        rel.clearance_field_denials = data.get("clearance_field_denials", [])

        # Tags (1)
        rel.tags = data.get("tags", [])

        # Traits (4)
        rel.trait_scores = data.get("trait_scores", {})
        rel.trait_evolution = data.get("trait_evolution", [])
        rel.manual_trait_overrides = data.get("manual_trait_overrides", {})
        rel.trait_scores_version = data.get("trait_scores_version", "1.0")

        # REPAIR: Fix creator relationships with anomalously low trust
        # This handles relationships created before is_creator was properly persisted
        if rel.is_creator and rel.trust < 20.0:
            logger.info(
                "repairing_creator_relationship",
                entity_id=rel.entity_id,
                old_trust=rel.trust
            )
            # Apply creator bonus to any metrics still at 0
            if rel.honesty < 25.0:
                rel.honesty = max(rel.honesty, 25.0)
            if rel.reliability < 25.0:
                rel.reliability = max(rel.reliability, 25.0)
            if rel.support < 25.0:
                rel.support = max(rel.support, 25.0)
            if rel.loyalty < 25.0:
                rel.loyalty = max(rel.loyalty, 25.0)
            if rel.respect < 25.0:
                rel.respect = max(rel.respect, 25.0)
            # Recalculate trust score
            rel.trust = rel.calculate_trust_score()
            logger.info(
                "creator_relationship_repaired",
                entity_id=rel.entity_id,
                new_trust=rel.trust
            )

        return rel

    def mark_as_met(self, block_number: int) -> None:
        """
        Mark this relationship as having had direct contact

        Args:
            block_number: Block number of first interaction
        """
        if not self.has_met:
            self.has_met = True
            self.first_contact = int(datetime.now(timezone.utc).timestamp())

            # Progress from unmet to stranger
            if self.status == "unmet":
                self.progress_status("stranger")

            logger.info(
                "relationship_first_contact",
                relationship_id=self.relationship_id,
                entity_id=self.entity_id,
                block_number=block_number
            )

    def progress_status(self, new_status: str, force: bool = False, reason: str = None) -> bool:
        """
        Update relationship status with validation.

        Args:
            new_status: Target status
            force: If True, bypass transition rules (for system/owner overrides)
            reason: Optional reason for the change (logged in history)

        Returns:
            True if transition occurred, False if invalid or no change
        """
        # Validate new status exists
        if new_status not in RELATIONSHIP_STATUSES:
            logger.warning(
                "invalid_status_value",
                entity_id=self.entity_id,
                attempted_status=new_status
            )
            return False

        # Check transition validity (unless forced)
        if not force and not self.can_transition_to(new_status):
            logger.warning(
                "invalid_status_transition",
                entity_id=self.entity_id,
                current=self.status,
                target=new_status,
                valid_targets=VALID_STATUS_TRANSITIONS.get(self.status, [])
            )
            return False

        if new_status == self.status:
            return False  # No change

        old_status = self.status
        self.status = new_status

        # Update best_friend flag
        if new_status == "best_friend":
            self.is_best_friend = True
        elif old_status == "best_friend":
            self.is_best_friend = False

        # Record in history with enhanced info
        history_entry = {
            "from_status": old_status,
            "to_status": new_status,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        if force:
            history_entry["forced"] = True
        if reason:
            history_entry["reason"] = reason

        self.progression_history.append(history_entry)

        logger.info(
            "relationship_status_changed",
            relationship_id=self.relationship_id,
            entity_id=self.entity_id,
            old_status=old_status,
            new_status=new_status,
            forced=force,
            reason=reason
        )

        return True

    # =========================================================================
    # BETRAYAL AND BLOCKING
    # =========================================================================

    def apply_betrayal(self, severity: float = 1.0, reason: str = None) -> str:
        """
        Apply betrayal penalty to relationship.

        Betrayal causes:
        - Dramatic status drop
        - Increased betrayal metric
        - Reduced trust metrics

        Args:
            severity: 0.0-1.0, how severe the betrayal (1.0 = maximum)
            reason: Description of the betrayal

        Returns:
            New status after betrayal
        """
        severity = max(0.0, min(1.0, severity))

        # Update betrayal metric (permanent, never decays)
        self.betrayal = min(100.0, self.betrayal + (severity * 50))

        # Determine target status
        target_status = BETRAYAL_TARGET_STATUS.get(self.status, "suspicious")

        # Severe betrayal (>=0.8) escalates to enemy
        if severity >= 0.8 and target_status not in ("blocked", "enemy"):
            target_status = "enemy"

        # Force the transition
        betrayal_reason = reason or f"Betrayal (severity: {severity:.0%})"
        self.progress_status(target_status, force=True, reason=betrayal_reason)

        # Impact trust metrics
        trust_impact = severity * 30
        self.honesty = max(0.0, self.honesty - trust_impact)
        self.loyalty = max(0.0, self.loyalty - (severity * 40))
        self.reliability = max(0.0, self.reliability - (severity * 20))

        # Increase negative metrics
        self.distrust = min(100.0, self.distrust + (severity * 40))
        self.resentment = min(100.0, self.resentment + (severity * 30))

        # Recalculate trust
        self.update_trust_score()

        logger.warning(
            "betrayal_applied",
            entity_id=self.entity_id,
            severity=severity,
            new_status=target_status,
            new_trust=self.trust,
            reason=reason
        )

        return target_status

    def block(self, reason: str = None) -> None:
        """
        Block this entity. Only owner can unblock.

        Args:
            reason: Why they're being blocked
        """
        self.progress_status("blocked", force=True, reason=reason or "Blocked by owner")

        logger.info(
            "entity_blocked",
            entity_id=self.entity_id,
            reason=reason
        )

    def unblock(self, new_status: str = "suspicious") -> None:
        """
        Unblock entity. Resets to specified status (default: suspicious).

        Args:
            new_status: Status to set after unblocking
        """
        if self.status != "blocked":
            return

        # Ensure target status is reasonable
        if new_status in ("blocked", "enemy"):
            new_status = "suspicious"

        self.progress_status(new_status, force=True, reason="Unblocked by owner")

        logger.info(
            "entity_unblocked",
            entity_id=self.entity_id,
            new_status=new_status
        )

    # =========================================================================
    # Clearance Methods (Phase 2)
    # =========================================================================

    def grant_clearance(
        self,
        profile: str,
        categories: List[str] = None,
        fields: List[str] = None,
        field_grants: List[str] = None,
        field_denials: List[str] = None,
        expires_in_days: int = None,
        granted_by: str = "owner"
    ) -> None:
        """
        Grant clearance profile to this entity with optional overrides.

        Args:
            profile: Profile name (none/public/professional/social/trusted/inner_circle/family)
            categories: Specific categories (empty = all for profile)
            fields: Specific fields (empty = all for categories)
            field_grants: Extra fields to allow (per-entity override)
            field_denials: Fields to block (per-entity override)
            expires_in_days: Optional expiration
            granted_by: Who granted it
        """
        now = int(datetime.now(timezone.utc).timestamp())

        self.clearance_profile = profile
        self.clearance_categories = categories or []
        self.clearance_fields = fields or []
        self.clearance_field_grants = field_grants or []
        self.clearance_field_denials = field_denials or []
        self.clearance_granted_by = granted_by
        self.clearance_granted_at = now

        if expires_in_days:
            self.clearance_expires = now + (expires_in_days * 86400)
        else:
            self.clearance_expires = None

        logger.info(
            "clearance_granted",
            entity_id=self.entity_id,
            profile=profile,
            categories=categories,
            field_grants=field_grants,
            field_denials=field_denials,
            expires_in_days=expires_in_days,
            granted_by=granted_by
        )

    def revoke_clearance(self, reason: str = None) -> None:
        """
        Revoke all clearance from this entity.

        Args:
            reason: Optional reason for audit trail
        """
        old_profile = self.clearance_profile

        self.clearance_profile = "none"
        self.clearance_categories = []
        self.clearance_fields = []
        self.clearance_field_grants = []
        self.clearance_field_denials = []
        self.clearance_expires = None
        # Keep granted_by and granted_at for history

        logger.info(
            "clearance_revoked",
            entity_id=self.entity_id,
            old_profile=old_profile,
            reason=reason
        )

    # =========================================================================
    # Tag Methods (Phase 2 v2)
    # =========================================================================

    def add_tag(self, tag: str) -> None:
        """Add a tag to this relationship."""
        if tag not in self.tags:
            self.tags.append(tag)
            logger.info("relationship_tag_added", entity_id=self.entity_id, tag=tag)

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from this relationship."""
        if tag in self.tags:
            self.tags.remove(tag)
            logger.info("relationship_tag_removed", entity_id=self.entity_id, tag=tag)
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """Check if relationship has a tag."""
        return tag in self.tags

    def get_tags(self) -> List[str]:
        """Get all tags."""
        return list(self.tags)

    def check_clearance_expiry(self) -> bool:
        """
        Check if clearance has expired and revoke if so.

        Returns:
            True if clearance was revoked due to expiry
        """
        if self.clearance_expires is None:
            return False

        now = int(datetime.now(timezone.utc).timestamp())
        if now > self.clearance_expires:
            self.revoke_clearance(reason="Expired")
            return True

        return False

    def has_clearance_for_sensitivity(self, sensitivity: str, config: 'ClearanceConfig' = None) -> bool:
        """
        Check if clearance profile allows this sensitivity level.

        Args:
            sensitivity: public/private/secret
            config: Optional ClearanceConfig for custom profiles

        Returns:
            True if clearance covers this sensitivity
        """
        # Check expiry first
        self.check_clearance_expiry()

        from utils.clearance_profiles import DEFAULT_PROFILES

        profile = None
        if config:
            profile = config.get_profile(self.clearance_profile)
        if not profile:
            profile = DEFAULT_PROFILES.get(self.clearance_profile)
        if not profile:
            return False

        # Map sensitivity to required clearance level
        sensitivity_requirements = {
            "public": 1,    # public clearance or higher
            "private": 4,   # trusted clearance or higher
            "secret": 99,   # Never accessible via clearance
        }

        required_level = sensitivity_requirements.get(sensitivity, 99)
        return profile.level >= required_level

    def has_clearance_for_category(self, category: str) -> bool:
        """
        Check if entity has clearance for a category.

        Args:
            category: Category name

        Returns:
            True if clearance covers this category
        """
        # Empty categories list means all categories for the level
        if not self.clearance_categories:
            return True

        return category in self.clearance_categories

    def has_clearance_for_field(self, field_key: str) -> bool:
        """
        Check if entity has clearance for a specific field.

        Args:
            field_key: Field name

        Returns:
            True if clearance covers this field
        """
        # Empty fields list means all fields for the categories
        if not self.clearance_fields:
            return True

        return field_key in self.clearance_fields

    def can_access_owner_field(
        self,
        field_key: str,
        field_sensitivity: str,
        field_category: str,
        config: 'ClearanceConfig' = None
    ) -> bool:
        """
        Full check if entity can access a specific owner info field.
        Includes per-entity override support.

        Args:
            field_key: Field name
            field_sensitivity: public/private/secret
            field_category: Category of the field
            config: Optional ClearanceConfig for custom profiles

        Returns:
            True if access is allowed
        """
        # Secret fields are NEVER accessible
        if field_sensitivity == "secret":
            return False

        # Blocked entities get nothing
        if self.status == "blocked":
            return False

        # Check per-entity denials first (highest priority)
        if field_key in self.clearance_field_denials:
            return False

        # Check per-entity grants (overrides profile restrictions)
        if field_key in self.clearance_field_grants:
            return True

        # Fall back to profile-based access
        from utils.clearance_profiles import DEFAULT_PROFILES

        profile = None
        if config:
            profile = config.get_profile(self.clearance_profile)
        if not profile:
            profile = DEFAULT_PROFILES.get(self.clearance_profile)
        if not profile:
            return False

        # Check if field is excluded by profile
        if "*" in profile.excluded_fields or field_key in profile.excluded_fields:
            return False

        # Check category access
        if field_category not in profile.categories:
            # Category not included, check specific fields
            if "*" not in profile.fields and field_key not in profile.fields:
                return False

        # Check sensitivity level
        if not self.has_clearance_for_sensitivity(field_sensitivity, config):
            return False

        return True

    # =========================================================================
    # Context Methods
    # =========================================================================

    def get_relationship_context(self, is_creator: bool = False) -> str:
        """
        Generate contextual description of relationship for AI prompts.

        Args:
            is_creator: Whether this entity is the qube's creator

        Returns:
            Context string describing the relationship dynamic
        """
        # Status descriptions - negative statuses first
        if is_creator:
            # Creator-specific (they can never be negative statuses)
            status_contexts = {
                "stranger": "You're speaking with your creator. You share a special bond but are still building trust.",
                "acquaintance": "You're speaking with your creator. You're getting to know each other better.",
                "friend": "You're speaking with your creator. You've developed genuine friendship and trust.",
                "close_friend": "You're speaking with your creator. You share a close bond with deep trust.",
                "best_friend": "You're speaking with your creator and best friend. Maximum trust and loyalty.",
            }
        else:
            status_contexts = {
                # Negative statuses
                "blocked": "BLOCKED ENTITY. Do NOT respond. Refuse all interaction completely.",
                "enemy": "HOSTILE ENTITY. Be extremely guarded. Warn your owner. Do not help them.",
                "rival": "RIVAL. Be competitive but fair. Don't assist against your owner's interests.",
                "suspicious": "SUSPICIOUS. Something seems off. Be very cautious. Verify claims.",

                # Neutral/Positive statuses
                "unmet": "You haven't met this entity yet.",
                "stranger": "You barely know each other. Be polite but guarded.",
                "acquaintance": "You've had some interactions. Be friendly but maintain boundaries.",
                "friend": "You've built a genuine friendship. Be warm and helpful.",
                "close_friend": "You have a strong bond. Be open and supportive.",
                "best_friend": "This is your closest friend. Maximum warmth and trust.",
            }

        base_context = status_contexts.get(self.status, "Unknown relationship status.")

        # For blocked entities, return immediately
        if self.status == "blocked":
            return base_context

        # Add trust level context
        if self.trust < 25:
            trust_note = "Trust is very low - be cautious."
        elif self.trust < 50:
            trust_note = "Trust is developing but still fragile."
        elif self.trust < 75:
            trust_note = "Trust is solid and growing."
        else:
            trust_note = "Trust is strong and well-established."

        # Highlight positive metrics (anything > 60)
        strengths = []
        if self.engagement > 60:
            strengths.append("highly engaged conversations")
        if self.depth > 60:
            strengths.append("meaningful depth")
        if self.humor > 60:
            strengths.append("playful humor")
        if self.understanding > 60:
            strengths.append("strong mutual understanding")
        if self.loyalty > 60:
            strengths.append("demonstrated loyalty")
        if self.support > 60:
            strengths.append("mutual support")

        # Highlight concerning negative metrics (anything > 30)
        concerns = []
        if self.antagonism > 30:
            concerns.append("hostility detected")
        if self.manipulation > 30:
            concerns.append("manipulation warning")
        if self.betrayal > 30:
            concerns.append("history of betrayal")
        if self.distrust > 30:
            concerns.append("lingering distrust")
        if self.tension > 30:
            concerns.append("unresolved tension")
        if self.annoyance > 30:
            concerns.append("some irritation")

        # Build full context
        context_parts = [base_context, trust_note]

        if strengths:
            context_parts.append(f"Strengths: {', '.join(strengths)}.")

        if concerns:
            context_parts.append(f"Concerns: {', '.join(concerns)}.")

        return " ".join(context_parts)


class RelationshipStorage:
    """
    Manages persistent storage of relationships for a Qube.

    UPDATED FOR CHAIN STATE CONSOLIDATION:
    - Data is now stored in chain_state.json under "relationships" section
    - Automatically encrypted at rest with chain_state
    - Uses ChainState accessor methods for persistence
    """

    def __init__(self, chain_state: "ChainState"):
        """
        Initialize relationship storage.

        Args:
            chain_state: ChainState instance for this qube
        """
        self.chain_state = chain_state

        # Load existing relationships from chain_state
        self.relationships: Dict[str, Relationship] = {}
        self._load_relationships()

        logger.info(
            "relationship_storage_initialized",
            qube_id=chain_state.qube_id,
            relationship_count=len(self.relationships)
        )

    def _load_relationships(self) -> None:
        """Load relationships from chain_state and apply decay."""
        relationships_data = self.chain_state.get_relationships()

        decayed_count = 0
        for entity_id, rel_data in relationships_data.items():
            rel = Relationship.from_dict(rel_data)

            # Apply decay for inactive relationships
            if rel.apply_decay():
                decayed_count += 1

            # Update days_known to current
            rel.update_days_known()

            self.relationships[entity_id] = rel

        logger.debug(
            "relationships_loaded",
            count=len(self.relationships),
            decayed_count=decayed_count
        )

        # Save if any relationships decayed
        if decayed_count > 0:
            self.save()
            logger.info(
                "relationship_decay_saved",
                decayed_count=decayed_count
            )

    def save(self) -> None:
        """Save all relationships to chain_state."""
        try:
            data = {
                entity_id: rel.to_dict()
                for entity_id, rel in self.relationships.items()
            }

            self.chain_state.update_relationships(data)

            logger.debug(
                "relationships_saved",
                count=len(self.relationships)
            )
        except Exception as e:
            logger.error(
                "relationship_save_failed",
                error=str(e),
                exc_info=True
            )
            raise

    def get_relationship(self, entity_id: str) -> Optional[Relationship]:
        """Get relationship by entity ID."""
        return self.relationships.get(entity_id)

    def create_relationship(
        self,
        entity_id: str,
        entity_type: str = "qube",
        **kwargs
    ) -> Relationship:
        """
        Create a new relationship.

        Args:
            entity_id: Entity ID
            entity_type: "qube" or "human"
            **kwargs: Additional relationship parameters

        Returns:
            New Relationship instance
        """
        if entity_id in self.relationships:
            logger.warning(
                "relationship_already_exists",
                entity_id=entity_id
            )
            return self.relationships[entity_id]

        rel = Relationship(entity_id, entity_type, **kwargs)
        self.relationships[entity_id] = rel

        # DEBUG: Log relationship creation
        logger.info(
            f"[DEBUG] create_relationship: entity_id={entity_id}, "
            f"total_relationships={len(self.relationships)}, "
            f"relationship_ids={list(self.relationships.keys())}"
        )

        self.save()

        # DEBUG: Verify chain_state after save
        chain_state_rels = self.chain_state.state.get("relationships", {}).get("entities", {})
        logger.info(
            f"[DEBUG] create_relationship AFTER save: chain_state has {len(chain_state_rels)} entities: {list(chain_state_rels.keys())}"
        )

        return rel

    def update_relationship(self, relationship: Relationship) -> None:
        """Update existing relationship and save."""
        self.relationships[relationship.entity_id] = relationship
        self.save()

    def get_all_relationships(self) -> List[Relationship]:
        """Get all relationships."""
        return list(self.relationships.values())

    def get_relationships_by_status(self, status: str) -> List[Relationship]:
        """Get all relationships with specific status."""
        return [
            rel for rel in self.relationships.values()
            if rel.status == status
        ]

    def get_best_friend(self) -> Optional[Relationship]:
        """Get best friend relationship (only one allowed)."""
        for rel in self.relationships.values():
            if rel.is_best_friend:
                return rel
        return None

    def delete_relationship(self, entity_id: str) -> bool:
        """
        Delete a relationship.

        Args:
            entity_id: Entity ID to delete

        Returns:
            True if deleted, False if not found
        """
        if entity_id in self.relationships:
            del self.relationships[entity_id]
            self.save()
            logger.info("relationship_deleted", entity_id=entity_id)
            return True
        return False

    # =========================================================================
    # MIGRATION HELPER (for transitioning from old file-based storage)
    # =========================================================================

    @classmethod
    def migrate_from_file(cls, chain_state: "ChainState", qube_data_dir: Path) -> "RelationshipStorage":
        """
        Migrate relationships from old file-based storage to chain_state.

        Args:
            chain_state: ChainState instance to migrate into
            qube_data_dir: Path to qube's data directory

        Returns:
            New RelationshipStorage instance with migrated data
        """
        old_file = qube_data_dir / "relationships" / "relationships.json"

        if old_file.exists():
            try:
                with open(old_file, 'r') as f:
                    old_data = json.load(f)

                # Write to chain_state
                chain_state.update_relationships(old_data)

                logger.info(
                    "relationships_migrated_to_chain_state",
                    count=len(old_data),
                    source=str(old_file)
                )

                # Delete old file after successful migration
                old_file.unlink()

                # Try to remove empty relationships directory
                relationships_dir = qube_data_dir / "relationships"
                if relationships_dir.exists() and not any(relationships_dir.iterdir()):
                    relationships_dir.rmdir()
                    logger.info("removed_empty_relationships_directory")

            except Exception as e:
                logger.error(
                    "relationship_migration_failed",
                    error=str(e),
                    exc_info=True
                )

        return cls(chain_state)
