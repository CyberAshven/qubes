"""
Social Dynamics Manager

High-level interface for managing all relationship operations.
Integrates relationship storage, trust scoring, and progression.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path

from relationships.relationship import Relationship, RelationshipStorage
from relationships.trust import TrustScorer
from relationships.progression import RelationshipProgressionManager
from utils.logging import get_logger

logger = get_logger(__name__)


class SocialDynamicsManager:
    """
    Main interface for relationship management

    UPDATED FOR CHAIN STATE CONSOLIDATION:
    - Now accepts RelationshipStorage instance instead of creating it
    - RelationshipStorage is initialized externally with ChainState

    Provides high-level methods for:
    - Creating and managing relationships
    - Recording interactions and collaborations
    - Calculating trust scores
    - Progressing relationship statuses
    - Managing best friends
    - Tracking shared experiences
    """

    def __init__(
        self,
        relationship_storage: RelationshipStorage,
        trust_profile: Optional[str] = None,
        qube = None
    ):
        """
        Initialize social dynamics manager

        Args:
            relationship_storage: RelationshipStorage instance (already initialized with ChainState)
            trust_profile: Default trust scoring profile ("analytical", "social", "cautious")
            qube: Reference to parent Qube (for creator detection)
        """
        self.storage = relationship_storage
        self.trust_profile = trust_profile
        self.qube = qube

        # Initialize components
        self.trust_scorer = TrustScorer()
        self.progression_manager = RelationshipProgressionManager(self.trust_scorer)

        logger.info(
            "social_dynamics_manager_initialized",
            trust_profile=trust_profile,
            relationship_count=len(self.storage.relationships)
        )

    # ========== Relationship CRUD ==========

    def get_relationship(self, entity_id: str) -> Optional[Relationship]:
        """
        Get relationship by entity ID

        Args:
            entity_id: Entity ID to look up

        Returns:
            Relationship or None if not found
        """
        return self.storage.get_relationship(entity_id)

    def create_relationship(
        self,
        entity_id: str,
        entity_type: str = "qube",
        public_key: Optional[str] = None,
        nft_address: Optional[str] = None,
        has_met: bool = False
    ) -> Relationship:
        """
        Create a new relationship

        Args:
            entity_id: Entity ID
            entity_type: "qube" or "human"
            public_key: Public key of entity
            nft_address: NFT address if Qube
            has_met: Whether direct interaction has occurred

        Returns:
            New Relationship instance
        """
        # Detect if this is the qube's creator
        is_creator = False
        if self.qube and hasattr(self.qube, 'user_name'):
            is_creator = (entity_id == self.qube.user_name and entity_type == "human")

        return self.storage.create_relationship(
            entity_id=entity_id,
            entity_type=entity_type,
            public_key=public_key,
            nft_address=nft_address,
            has_met=has_met,
            is_creator=is_creator
        )

    def get_or_create_relationship(
        self,
        entity_id: str,
        **kwargs
    ) -> Relationship:
        """
        Get existing relationship or create if doesn't exist

        Args:
            entity_id: Entity ID
            **kwargs: Additional relationship parameters if creating

        Returns:
            Relationship instance
        """
        rel = self.storage.get_relationship(entity_id)
        if rel:
            return rel

        return self.create_relationship(entity_id, **kwargs)

    def get_all_relationships(self) -> List[Relationship]:
        """Get all relationships"""
        return self.storage.get_all_relationships()

    def get_relationships_by_status(self, status: str) -> List[Relationship]:
        """
        Get all relationships with specific status

        Args:
            status: Status filter (unmet/stranger/acquaintance/friend/close_friend/best_friend)

        Returns:
            List of matching relationships
        """
        return self.storage.get_relationships_by_status(status)

    def get_friends(self) -> List[Relationship]:
        """Get all friend-level relationships (friend, close_friend, best_friend)"""
        return [
            rel for rel in self.storage.get_all_relationships()
            if rel.relationship_status in ["friend", "close_friend", "best_friend"]
        ]

    def get_best_friend(self) -> Optional[Relationship]:
        """Get best friend (only one allowed)"""
        return self.storage.get_best_friend()

    def delete_relationship(self, entity_id: str) -> bool:
        """
        Delete a relationship

        Args:
            entity_id: Entity ID to delete

        Returns:
            True if deleted, False if not found
        """
        return self.storage.delete_relationship(entity_id)

    # ========== Interaction Handling ==========

    def record_message(
        self,
        entity_id: str,
        is_outgoing: bool,
        response_time_seconds: Optional[float] = None,
        auto_create: bool = True
    ) -> Relationship:
        """
        Record a message interaction

        Args:
            entity_id: Entity ID
            is_outgoing: True if sent, False if received
            response_time_seconds: Response time if incoming message
            auto_create: Create relationship if doesn't exist

        Returns:
            Updated Relationship
        """
        rel = self.storage.get_relationship(entity_id)

        if not rel:
            if auto_create:
                rel = self.create_relationship(entity_id, has_met=True)
            else:
                raise ValueError(f"No relationship found for {entity_id}")

        # Record interaction
        self.progression_manager.handle_interaction(
            rel,
            is_outgoing,
            response_time_seconds
        )

        # Update friendship metrics
        self.progression_manager.update_friendship_metrics(rel)

        # Check for progression
        self.progression_manager.check_and_progress(rel, self.trust_profile)

        # Save changes
        self.storage.update_relationship(rel)

        return rel

    def record_collaboration(
        self,
        entity_id: str,
        succeeded: bool,
        importance: float = 1.0
    ) -> Relationship:
        """
        Record a collaboration outcome

        Args:
            entity_id: Entity ID
            succeeded: Whether collaboration succeeded
            importance: Importance multiplier (0.1 to 3.0)

        Returns:
            Updated Relationship
        """
        rel = self.storage.get_relationship(entity_id)
        if not rel:
            raise ValueError(f"No relationship found for {entity_id}")

        # Handle collaboration
        self.progression_manager.handle_collaboration_outcome(
            rel,
            succeeded,
            importance
        )

        # Update friendship metrics
        self.progression_manager.update_friendship_metrics(rel)

        # Check for progression
        self.progression_manager.check_and_progress(rel, self.trust_profile)

        # Save changes
        self.storage.update_relationship(rel)

        return rel

    def record_shared_experience(
        self,
        entity_id: str,
        event: str,
        sentiment: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Relationship:
        """
        Record a shared experience

        Args:
            entity_id: Entity ID
            event: Description of experience
            sentiment: "positive", "negative", or "neutral"
            details: Additional details

        Returns:
            Updated Relationship
        """
        rel = self.storage.get_relationship(entity_id)
        if not rel:
            raise ValueError(f"No relationship found for {entity_id}")

        rel.add_shared_experience(event, sentiment, details)

        # Update friendship metrics
        self.progression_manager.update_friendship_metrics(rel)

        # Save changes
        self.storage.update_relationship(rel)

        return rel

    # ========== Trust Management ==========

    def calculate_trust_score(
        self,
        entity_id: str,
        profile: Optional[str] = None
    ) -> float:
        """
        Calculate current trust score for an entity

        Args:
            entity_id: Entity ID
            profile: Trust profile override (None = use manager default)

        Returns:
            Trust score 0-100
        """
        rel = self.storage.get_relationship(entity_id)
        if not rel:
            raise ValueError(f"No relationship found for {entity_id}")

        profile = profile or self.trust_profile
        score = self.trust_scorer.calculate_trust_score(rel, profile)

        # Update stored score
        rel.overall_trust_score = score
        self.storage.update_relationship(rel)

        return score

    def update_trust_component(
        self,
        entity_id: str,
        component: str,
        delta: float,
        reason: Optional[str] = None
    ) -> None:
        """
        Manually adjust a trust component

        Args:
            entity_id: Entity ID
            component: Component to update ("reliability", "honesty", "responsiveness")
            delta: Change amount (-100 to +100)
            reason: Optional reason
        """
        rel = self.storage.get_relationship(entity_id)
        if not rel:
            raise ValueError(f"No relationship found for {entity_id}")

        self.trust_scorer.update_trust_component(rel, component, delta, reason)
        self.storage.update_relationship(rel)

    def update_expertise(
        self,
        entity_id: str,
        domain: str,
        score: float
    ) -> None:
        """
        Update expertise score for a domain

        Args:
            entity_id: Entity ID
            domain: Expertise domain
            score: Score 0-100
        """
        rel = self.storage.get_relationship(entity_id)
        if not rel:
            raise ValueError(f"No relationship found for {entity_id}")

        rel.update_expertise(domain, score)
        self.storage.update_relationship(rel)

    def apply_penalty(
        self,
        entity_id: str,
        penalty_type: str,
        reason: str
    ) -> None:
        """
        Apply a trust penalty

        Args:
            entity_id: Entity ID
            penalty_type: "warning" or "dispute"
            reason: Reason for penalty
        """
        rel = self.storage.get_relationship(entity_id)
        if not rel:
            raise ValueError(f"No relationship found for {entity_id}")

        self.trust_scorer.apply_penalty(rel, penalty_type, reason)
        self.storage.update_relationship(rel)

    # ========== Third-Party Reputation ==========

    def add_third_party_opinion(
        self,
        subject_id: str,
        observer_id: str,
        trust_score: float,
        relationship_type: str
    ) -> None:
        """
        Record someone else's opinion about an entity

        Args:
            subject_id: Entity being evaluated
            observer_id: Entity giving opinion
            trust_score: Their trust score (0-100)
            relationship_type: Their relationship type
        """
        # Get or create relationship for subject
        rel = self.get_or_create_relationship(subject_id, has_met=False)

        rel.add_third_party_opinion(observer_id, trust_score, relationship_type)
        self.storage.update_relationship(rel)

    # ========== Relationship Progression ==========

    def check_progression(self, entity_id: str) -> bool:
        """
        Check if relationship can progress and update

        Args:
            entity_id: Entity ID

        Returns:
            True if progressed, False otherwise
        """
        rel = self.storage.get_relationship(entity_id)
        if not rel:
            raise ValueError(f"No relationship found for {entity_id}")

        progressed = self.progression_manager.check_and_progress(rel, self.trust_profile)

        if progressed:
            self.storage.update_relationship(rel)

        return progressed

    def designate_best_friend(self, entity_id: str) -> bool:
        """
        Manually designate someone as best friend

        Args:
            entity_id: Entity ID to promote

        Returns:
            True if successful, False if requirements not met
        """
        rel = self.storage.get_relationship(entity_id)
        if not rel:
            raise ValueError(f"No relationship found for {entity_id}")

        current_best = self.storage.get_best_friend()

        success = self.progression_manager.designate_best_friend(rel, current_best)

        if success:
            self.storage.update_relationship(rel)
            if current_best:
                self.storage.update_relationship(current_best)

        return success

    # ========== Statistics ==========

    def get_relationship_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics about all relationships

        Returns:
            Dictionary with relationship statistics
        """
        all_rels = self.storage.get_all_relationships()

        status_counts = {}
        for status in ["unmet", "stranger", "acquaintance", "friend", "close_friend", "best_friend"]:
            status_counts[status] = len(self.get_relationships_by_status(status))

        avg_trust = sum(r.overall_trust_score for r in all_rels) / len(all_rels) if all_rels else 0

        return {
            "total_relationships": len(all_rels),
            "status_breakdown": status_counts,
            "average_trust_score": round(avg_trust, 2),
            "total_collaborations": sum(r.total_collaborations for r in all_rels),
            "successful_collaborations": sum(r.successful_joint_tasks for r in all_rels),
            "best_friend": self.get_best_friend().entity_id if self.get_best_friend() else None
        }

    def get_top_relationships(self, limit: int = 10) -> List[Relationship]:
        """
        Get top relationships by trust score

        Args:
            limit: Maximum number to return

        Returns:
            List of top relationships
        """
        all_rels = self.storage.get_all_relationships()
        sorted_rels = sorted(all_rels, key=lambda r: r.overall_trust_score, reverse=True)
        return sorted_rels[:limit]
