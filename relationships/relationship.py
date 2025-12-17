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

        # Creator Bonus: Start with elevated metrics for qube-creator relationships
        if is_creator:
            # Core Trust Metrics
            self.honesty = 25.0
            self.reliability = 25.0
            self.support = 25.0
            self.loyalty = 25.0
            self.respect = 25.0

            # Positive Social Metrics
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

            # Update trust score based on new core trust values
            self.trust = self.calculate_trust_score()

            logger.info(
                "creator_relationship_initialized",
                entity_id=entity_id,
                trust=self.trust
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
            # Essential Identity (4)
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "relationship_id": self.relationship_id,
            "public_key": self.public_key,

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
            "evaluations": self.evaluations
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """Load relationship from dictionary"""
        rel = cls(
            entity_id=data["entity_id"],
            entity_type=data.get("entity_type", "qube"),
            public_key=data.get("public_key"),
            has_met=data.get("has_met", False)
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

    def progress_status(self, new_status: str) -> None:
        """
        Update relationship status

        Args:
            new_status: New relationship status
        """
        if new_status != self.status:
            old_status = self.status
            self.status = new_status

            self.progression_history.append({
                "status": new_status,
                "timestamp": int(datetime.now(timezone.utc).timestamp())
            })

            logger.info(
                "relationship_status_changed",
                relationship_id=self.relationship_id,
                entity_id=self.entity_id,
                old_status=old_status,
                new_status=new_status
            )

    def get_relationship_context(self, is_creator: bool = False) -> str:
        """
        Generate contextual description of relationship for AI prompts

        Args:
            is_creator: Whether this entity is the qube's creator

        Returns:
            Context string describing the relationship dynamic
        """
        # Base status descriptions
        if is_creator:
            status_contexts = {
                "stranger": "You're speaking with your creator. You share a special bond but are still building trust and getting to know each other.",
                "acquaintance": "You're speaking with your creator. You're getting to know each other better and building mutual understanding.",
                "friend": "You're speaking with your creator. You've developed a genuine friendship with trust and mutual respect.",
                "close_friend": "You're speaking with your creator. You share a close bond with deep trust and understanding.",
                "best_friend": "You're speaking with your creator and best friend. You share the deepest level of trust, loyalty, and connection."
            }
        else:
            status_contexts = {
                "stranger": "You barely know each other. Tread carefully and build trust gradually.",
                "acquaintance": "You've had some interactions but the relationship is still developing. Continue building trust through genuine exchanges.",
                "friend": "You've established a solid friendship with mutual respect and trust. Be authentic and supportive.",
                "close_friend": "You have a strong bond with deep mutual trust and understanding. You can be vulnerable and honest with each other.",
                "best_friend": "This is your closest relationship. You share profound trust, loyalty, and connection. Be yourself completely."
            }

        base_context = status_contexts.get(self.status, "You have some history with this person.")

        # Add trust level context
        if self.trust < 25:
            trust_note = "Trust is very low - be cautious."
        elif self.trust < 50:
            trust_note = "Trust is developing but still fragile."
        elif self.trust < 75:
            trust_note = "Trust is solid and growing."
        else:
            trust_note = "Trust is strong and well-established."

        # Highlight top positive metrics (anything > 60)
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

        # Highlight notable negative metrics (anything > 30)
        concerns = []
        if self.annoyance > 30:
            concerns.append("some irritation")
        if self.tension > 30:
            concerns.append("unresolved tension")
        if self.distrust > 30:
            concerns.append("lingering distrust")
        if self.rivalry > 30:
            concerns.append("competitive tension")

        # Build full context
        context_parts = [base_context, trust_note]

        if strengths:
            context_parts.append(f"Strengths: {', '.join(strengths)}.")

        if concerns:
            context_parts.append(f"Areas of friction: {', '.join(concerns)}.")

        return " ".join(context_parts)


class RelationshipStorage:
    """
    Manages persistent storage of relationships for a Qube
    """

    def __init__(self, qube_data_dir: Path):
        """
        Initialize relationship storage

        Args:
            qube_data_dir: Path to Qube's data directory (e.g., data/qubes/Alice_A1B2C3D4/)
        """
        self.qube_data_dir = Path(qube_data_dir)
        self.relationships_dir = self.qube_data_dir / "relationships"
        self.relationships_file = self.relationships_dir / "relationships.json"

        # Ensure directory exists
        self.relationships_dir.mkdir(parents=True, exist_ok=True)

        # Load existing relationships
        self.relationships: Dict[str, Relationship] = {}
        self._load_relationships()

        logger.info(
            "relationship_storage_initialized",
            qube_dir=str(self.qube_data_dir),
            relationship_count=len(self.relationships)
        )

    def _load_relationships(self) -> None:
        """Load relationships from JSON file and apply decay"""
        if self.relationships_file.exists():
            try:
                with open(self.relationships_file, 'r') as f:
                    data = json.load(f)

                decayed_count = 0
                for entity_id, rel_data in data.items():
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

            except Exception as e:
                logger.error(
                    "relationship_load_failed",
                    error=str(e),
                    exc_info=True
                )
        else:
            logger.debug("no_existing_relationships_file")

    def save(self) -> None:
        """Save all relationships to JSON file"""
        try:
            data = {
                entity_id: rel.to_dict()
                for entity_id, rel in self.relationships.items()
            }

            with open(self.relationships_file, 'w') as f:
                json.dump(data, f, indent=2)

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
        """Get relationship by entity ID"""
        return self.relationships.get(entity_id)

    def create_relationship(
        self,
        entity_id: str,
        entity_type: str = "qube",
        **kwargs
    ) -> Relationship:
        """
        Create a new relationship

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
        self.save()

        return rel

    def update_relationship(self, relationship: Relationship) -> None:
        """Update existing relationship and save"""
        self.relationships[relationship.entity_id] = relationship
        self.save()

    def get_all_relationships(self) -> List[Relationship]:
        """Get all relationships"""
        return list(self.relationships.values())

    def get_relationships_by_status(self, status: str) -> List[Relationship]:
        """Get all relationships with specific status"""
        return [
            rel for rel in self.relationships.values()
            if rel.status == status
        ]

    def get_best_friend(self) -> Optional[Relationship]:
        """Get best friend relationship (only one allowed)"""
        for rel in self.relationships.values():
            if rel.is_best_friend:
                return rel
        return None

    def delete_relationship(self, entity_id: str) -> bool:
        """
        Delete a relationship

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
